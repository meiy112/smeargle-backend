package service

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"sync"

	"github.com/google/uuid"
)

type Layer struct {
	Title  string
	Canvas string
}

type ComponentData struct {
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
		// Call the upgraded recursive rectangle detection script.
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
		if parsedData[i].ID == "" {
			parsedData[i].ID = uuid.New().String()
		}
	}

	results <- parsedData
}
