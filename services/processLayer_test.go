package main

import (
	"encoding/base64"
	"sync"
	"testing"
)

func TestProcessLayer(t *testing.T) {
	sampleBase64 := "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PyLGzQAAAABJRU5ErkJggg=="
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

	var output string
	for res := range results {
		output = res
	}

	if output == "" {
		t.Error("Expected output from processLayer, got empty string")
	} else {
		t.Logf("processLayer output: %s", output)
	}
}