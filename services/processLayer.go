package main

import (
	"encoding/base64"
	"fmt"
	"os"
	"os/exec"
	"sync"
	"io/ioutil"
)

type Layer struct {
	Title  string
	Canvas string
}

func processLayer(layer Layer, wg *sync.WaitGroup, results chan<- string) {
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
		cmd = exec.Command("python3", "scripts/detect_text.py", tmpfile.Name(), layer.Title)
	} else {
		cmd = exec.Command("python3", "scripts/detect_rectangles.py", tmpfile.Name(), layer.Title)
	}

	output, err := cmd.CombinedOutput()
	if err != nil {
		results <- fmt.Sprintf("Python error for %s: %v, output: %s", layer.Title, err, output)
		return
	}

	results <- fmt.Sprintf("Result for %s: %s", layer.Title, output)
}

func main() {
	imgData, err := ioutil.ReadFile("../images/smeargle.jpg")
	if err != nil {
		log.Fatalf("Error reading image file: %v", err)
	}

	sampleBase64 := base64.StdEncoding.EncodeToString(imgData)

	sampleLayer := Layer{
		Title:  "Box",
		Canvas: sampleBase64,
	}

	var wg sync.WaitGroup
	results := make(chan string, 1)

	wg.Add(1)
	go processLayer(sampleLayer, &wg, results)

	wg.Wait()
	close(results)

	for res := range results {
		fmt.Println(res)
	}
}