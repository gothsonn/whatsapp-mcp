package main

import (
	"os"
	"testing"
	"time"

	waProto "go.mau.fi/whatsmeow/binary/proto"
	"google.golang.org/protobuf/proto"
)

func TestExtractQuotedText(t *testing.T) {
	reply := &waProto.Message{ExtendedTextMessage: &waProto.ExtendedTextMessage{
		Text: proto.String("pode corrigir"),
		ContextInfo: &waProto.ContextInfo{QuotedMessage: &waProto.Message{
			Conversation: proto.String("[BBTS #46241] review"),
		}},
	}}
	if got := extractQuotedText(reply); got != "[BBTS #46241] review" {
		t.Fatalf("quoted = %q", got)
	}
	if got := extractQuotedText(&waProto.Message{Conversation: proto.String("oi")}); got != "" {
		t.Fatalf("plain message quoted = %q", got)
	}
	if got := extractQuotedText(nil); got != "" {
		t.Fatalf("nil quoted = %q", got)
	}
}

func TestQuotedContentIsStoredAndMigrationIsIdempotent(t *testing.T) {
	dir := t.TempDir()
	wd, _ := os.Getwd()
	defer os.Chdir(wd)
	if err := os.Chdir(dir); err != nil {
		t.Fatal(err)
	}
	store, err := NewMessageStore()
	if err != nil {
		t.Fatal(err)
	}
	store.Close()
	store, err = NewMessageStore()
	if err != nil {
		t.Fatalf("second open: %v", err)
	}
	defer store.Close()
	if err := store.StoreChat("c@lid", "c", time.Now()); err != nil {
		t.Fatal(err)
	}
	if err := store.StoreMessage("m1", "c@lid", "c", "pode corrigir", time.Now(), false, "", "", "", nil, nil, nil, 0); err != nil {
		t.Fatal(err)
	}
	if err := store.StoreQuotedContent("m1", "c@lid", "[BBTS #46241] review"); err != nil {
		t.Fatal(err)
	}
	var quoted string
	if err := store.db.QueryRow(`SELECT quoted_content FROM messages WHERE id = 'm1'`).Scan(&quoted); err != nil {
		t.Fatal(err)
	}
	if quoted != "[BBTS #46241] review" {
		t.Fatalf("stored quoted = %q", quoted)
	}
}
