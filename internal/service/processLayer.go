package service

import (
	"encoding/base64"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"sync"
)

type Layer struct {
	Title  string
	Canvas string
}

func ProcessLayer(layer Layer, wg *sync.WaitGroup, results chan<- string) {
	defer wg.Done()

	data, err := base64.StdEncoding.DecodeString(layer.Canvas)
	if err != nil {
		results <- fmt.Sprintf("Error decoding image for %s: %v", layer.Title, err)
		return
	}

	tmpfile, err := ioutil.TempFile("", "canvas-*.png")
	if err != nil {
		results <- fmt.Sprintf("Error creating temp file for %s: %v", layer.Title, err)
		return
	}
	defer os.Remove(tmpfile.Name())
	if _, err := tmpfile.Write(data); err != nil {
		results <- fmt.Sprintf("Error writing to temp file for %s: %v", layer.Title, err)
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
		results <- fmt.Sprintf("Python error for %s: %v, output: %s", layer.Title, err, output)
		return
	}

	results <- fmt.Sprintf("Result for %s: %s", layer.Title, output)
}
