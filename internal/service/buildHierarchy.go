package service

import (
	"sort"
)

func isInside(child, parent ComponentData) bool {
	return child.X >= parent.X &&
		child.Y >= parent.Y &&
		(child.X+child.Width) <= (parent.X+parent.Width) &&
		(child.Y+child.Height) <= (parent.Y+parent.Height)
}

func BuildHierarchy(components []ComponentData) []ComponentData {
	if len(components) == 0 {
		return []ComponentData{}
	}

	comps := make([]ComponentData, len(components))
	copy(comps, components)

	sort.Slice(comps, func(i, j int) bool {
		areaI := comps[i].Width * comps[i].Height
		areaJ := comps[j].Width * comps[j].Height
		return areaI < areaJ
	})

	assigned := make([]bool, len(comps))

	for i := 0; i < len(comps); i++ {
		for j := i + 1; j < len(comps); j++ {
			if comps[i].ID == comps[j].ID {
				continue
			}

			if isInside(comps[i], comps[j]) {
				comps[j].Children = append(comps[j].Children, comps[i])
				assigned[i] = true
				break
			}
		}
	}

	var topLevel []ComponentData
	for i, comp := range comps {
		if !assigned[i] {
			topLevel = append(topLevel, comp)
		}
	}

	return topLevel
}
