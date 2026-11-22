// Cross-verification: notes and C2SP cosignatures produced by the Python
// implementation are opened with golang.org/x/mod/sumdb/note and torchwood's
// CosignatureVerifier. Input: one JSON object per line on stdin.
package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"

	"filippo.io/torchwood"
	"golang.org/x/mod/sumdb/note"
)

type testCase struct {
	ID           string `json:"id"`
	LogVkey      string `json:"log_vkey"`
	CosignerVkey string `json:"cosigner_vkey"`
	Note         string `json:"note"`
	Expect       bool   `json:"expect"`
}

func main() {
	scanner := bufio.NewScanner(os.Stdin)
	scanner.Buffer(make([]byte, 1<<20), 1<<20)
	pass, total := 0, 0
	for scanner.Scan() {
		var c testCase
		if err := json.Unmarshal(scanner.Bytes(), &c); err != nil {
			panic(err)
		}
		logV, err := note.NewVerifier(c.LogVkey)
		if err != nil {
			panic(err)
		}
		cosV, err := torchwood.NewCosignatureVerifier(c.CosignerVkey)
		if err != nil {
			fmt.Printf("FAIL %s: cosigner vkey rejected: %v\n", c.ID, err)
			total++
			continue
		}
		n, err := note.Open([]byte(c.Note), note.VerifierList(logV, cosV))
		ok := err == nil
		if ok {
			names := map[string]bool{}
			for _, s := range n.Sigs {
				names[s.Name] = true
			}
			ok = names[logV.Name()] && names[cosV.Name()]
		}
		total++
		if ok == c.Expect {
			pass++
			fmt.Printf("PASS %s (verified=%v)\n", c.ID, ok)
		} else {
			fmt.Printf("FAIL %s (verified=%v, expected %v, err=%v)\n", c.ID, ok, c.Expect, err)
		}
	}
	fmt.Printf("%d/%d cases as expected\n", pass, total)
	if pass != total {
		os.Exit(1)
	}
}
