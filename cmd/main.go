package main

import (
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
	"github.com/meiy112/smeargle-backend/internal/service"
)

type Layer struct {
	Title  string `json:"title"`
	Canvas string `json:"canvas"`
}

type ProcessRequest struct {
	Layers []Layer `json:"layers"`
}

func main() {
	r := gin.Default()
	r.Use(cors.New(cors.Config{
		AllowOrigins:     []string{"http://localhost:3000"},
		AllowMethods:     []string{"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Authorization"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
		MaxAge:           12 * time.Hour,
	}))

	r.GET("/ping", func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"message": "pong"})
	})

	r.POST("/process", func(c *gin.Context) {
		var req ProcessRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
			return
		}

		var wg sync.WaitGroup
		resultsChan := make(chan []service.ComponentData, len(req.Layers))
		for _, layer := range req.Layers {
			wg.Add(1)
			go service.ProcessLayer(service.Layer{Title: layer.Title, Canvas: layer.Canvas}, &wg, resultsChan)
		}
		wg.Wait()
		close(resultsChan)

		hierarchical := []service.ComponentData{}
		for components := range resultsChan {
			if len(components) == 0 {
				continue
			}
			hierarchical = append(hierarchical, components...)
		}

		fmt.Print("border colour", hierarchical[0].BorderColor)

		c.JSON(http.StatusOK, gin.H{
			"status":  "Processed layers concurrently",
			"results": hierarchical,
		})
	})

	r.Run(":8080")
}
