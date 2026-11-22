// Interop harness: the real torchwood witness (internal/witness) served over local TLS.
// Usage: interopwitness <db> <log-origin> <log-verifier-key> <out-dir>
// Writes <out-dir>/url, <out-dir>/cert.pem and <out-dir>/witness_vkey, then serves forever.
package main

import (
	"crypto/ed25519"
	"encoding/base64"
	"encoding/pem"
	"log/slog"
	"net/http/httptest"
	"os"
	"path/filepath"

	"filippo.io/torchwood/internal/witness"
	"golang.org/x/mod/sumdb/tlog"
	"zombiezen.com/go/sqlite/sqlitex"
)

func main() {
	db, origin, vkey, out := os.Args[1], os.Args[2], os.Args[3], os.Args[4]
	seed := make([]byte, 32)
	for i := range seed {
		seed[i] = byte(200 + i)
	}
	key := ed25519.NewKeyFromSeed(seed)
	logger := slog.New(slog.NewTextHandler(os.Stderr, &slog.HandlerOptions{Level: slog.LevelDebug}))
	w, err := witness.NewWitness(db, "witness.example/interop", key, logger)
	if err != nil {
		panic(err)
	}
	conn, err := witness.OpenDB(db)
	if err != nil {
		panic(err)
	}
	empty, _ := tlog.TreeHash(0, nil)
	if err := sqlitex.Execute(conn, "INSERT OR IGNORE INTO log (origin, tree_size, tree_hash) VALUES (?, 0, ?)",
		&sqlitex.ExecOptions{Args: []any{origin, base64.StdEncoding.EncodeToString(empty[:])}}); err != nil {
		panic(err)
	}
	if err := sqlitex.Execute(conn, "INSERT INTO key (origin, key) VALUES (?, ?)",
		&sqlitex.ExecOptions{Args: []any{origin, vkey}}); err != nil {
		panic(err)
	}
	conn.Close()
	srv := httptest.NewUnstartedServer(w)
	srv.StartTLS()
	cert := pem.EncodeToMemory(&pem.Block{Type: "CERTIFICATE", Bytes: srv.Certificate().Raw})
	_ = os.WriteFile(filepath.Join(out, "cert.pem"), cert, 0o644)
	_ = os.WriteFile(filepath.Join(out, "witness_vkey"), []byte(w.VerifierKey()), 0o644)
	_ = os.WriteFile(filepath.Join(out, "url"), []byte(srv.URL), 0o644)
	select {}
}
