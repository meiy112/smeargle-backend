package service

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"image"
	"io/ioutil"
	"os"
	"os/exec"
	"sync"

	"github.com/google/uuid"
	"gocv.io/x/gocv"
)

type Layer struct {
	Title  string
	Canvas string
}

type ComponentData struct {
	// Common attributes for both types
	ID       string          `json:"id"`
	Title    string          `json:"title"`
	X        int             `json:"x"`
	Y        int             `json:"y"`
	Width    int             `json:"width"`
	Height   int             `json:"height"`
	Children []ComponentData `json:"children,omitempty"`

	// Text-specific attributes
	Word       string  `json:"word,omitempty"`
	FontSize   int     `json:"font_size,omitempty"`
	FontColor  string  `json:"font_color,omitempty"`
	FontWeight float64 `json:"font_weight,omitempty"`

	// Rectangle-specific attributes
	BorderWidth     int    `json:"border_width,omitempty"`
	BorderColor     string `json:"border_color,omitempty"`
	BackgroundColor string `json:"background_color,omitempty"`

	// Extra fields returned by Python for recursion.
	InnerX      int `json:"inner_x,omitempty"`
	InnerY      int `json:"inner_y,omitempty"`
	InnerWidth  int `json:"inner_width,omitempty"`
	InnerHeight int `json:"inner_height,omitempty"`
}

func ProcessSubLayer(originalPath string, rect ComponentData, minSize int) ([]ComponentData, error) {
	if rect.InnerWidth < minSize || rect.InnerHeight < minSize {
		return nil, nil
	}

	img := gocv.IMRead(originalPath, gocv.IMReadUnchanged)
	if img.Empty() {
		return nil, fmt.Errorf("failed to read image")
	}
	defer img.Close()

	roi := image.Rect(rect.InnerX, rect.InnerY, rect.InnerX+rect.InnerWidth, rect.InnerY+rect.InnerHeight)
	cropped := img.Region(roi)
	defer cropped.Close()

	tmpfile, err := ioutil.TempFile("", "subcanvas-*.png")
	if err != nil {
		return nil, err
	}
	defer os.Remove(tmpfile.Name())

	if ok := gocv.IMWrite(tmpfile.Name(), cropped); !ok {
		return nil, fmt.Errorf("failed to write cropped image")
	}

	cmd := exec.Command("python3", "internal/scripts/detect_rectangles.py", tmpfile.Name(), rect.Title)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return nil, fmt.Errorf("python error: %v, output: %s", err, output)
	}

	var children []ComponentData
	if err := json.Unmarshal(output, &children); err != nil {
		return nil, err
	}

	for i := range children {
		children[i].ID = uuid.New().String()
	}
	return children, nil
}

func ProcessLayer(layer Layer, wg *sync.WaitGroup, results chan<- []ComponentData) {
	defer wg.Done()

	data, err := base64.StdEncoding.DecodeString(layer.Canvas)
	if err != nil {
		fmt.Printf("Error decoding image for %s: %v", layer.Title, err)
		results <- nil
		return
	}

	tmpfile, err := ioutil.TempFile("", "canvas-*.png")
	if err != nil {
		fmt.Printf("Error creating temp file for %s: %v", layer.Title, err)
		results <- nil
		return
	}
	defer os.Remove(tmpfile.Name())
	if _, err := tmpfile.Write(data); err != nil {
		fmt.Printf("Error writing to temp file for %s: %v", layer.Title, err)
		results <- nil
		return
	}
	tmpfile.Close()

	var cmd *exec.Cmd
	if layer.Title == "Text" {
		cmd = exec.Command("python3", "internal/scripts/detect_text.py", tmpfile.Name(), layer.Title)
	} else {
		cmd = exec.Command("python3", "internal/scripts/detect_rectangles.py", tmpfile.Name(), layer.Title)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		fmt.Printf("Python error for %s: %v, output: %s", layer.Title, err, output)
		results <- nil
		return
	}

	var parsedData []ComponentData
	if err := json.Unmarshal(output, &parsedData); err != nil {
		fmt.Printf("Error parsing JSON for %s: %v\n", layer.Title, err)
		results <- nil
		return
	}

	for i := range parsedData {
		parsedData[i].ID = uuid.New().String()
	}

	var recWg sync.WaitGroup
	for i, rect := range parsedData {
		if rect.InnerWidth >= 50 && rect.InnerHeight >= 50 {
			recWg.Add(1)
			go func(i int, rect ComponentData) {
				defer recWg.Done()
				children, err := ProcessSubLayer(tmpfile.Name(), rect, 50)
				if err != nil {
					fmt.Printf("Error processing sublayer for rect %s: %v\n", rect.ID, err)
					return
				}
				parsedData[i].Children = children
			}(i, rect)
		}
	}
	recWg.Wait()

	results <- parsedData
}
