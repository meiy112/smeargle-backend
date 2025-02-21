package service

import (
	"encoding/base64"
	"io/ioutil"
	"path/filepath"
	"sync"
	"testing"
)

func TestProcessLayer(t *testing.T) {
	absPath, err := filepath.Abs("../../images/smeargle.jpg")
	if err != nil {
		t.Fatalf("Error getting absolute path: %v", err)
	}

	// Read the file contents.
	imgData, err := ioutil.ReadFile(absPath)
	if err != nil {
		t.Fatalf("Error reading image file: %v", err)
	}

	// Encode the image data to base64.
	sampleBase64 := base64.StdEncoding.EncodeToString(imgData)

	sampleLayer := Layer{
		Title:  "Box",
		Canvas: sampleBase64,
	}

	var wg sync.WaitGroup
	results := make(chan string, 1)

	wg.Add(1)
	go ProcessLayer(sampleLayer, &wg, results)
	wg.Wait()
	close(results)

	var output string
	for res := range results {
		output = res
	}

	if output == "" {
		t.Error("Expected output from ProcessLayer, got empty string")
	} else {
		t.Logf("ProcessLayer output: %s", output)
	}
}
