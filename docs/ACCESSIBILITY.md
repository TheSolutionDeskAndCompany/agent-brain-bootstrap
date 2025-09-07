# Accessibility (iPhone + Amazon Fire)

## Screen readers
- iPhone: VoiceOver (Settings → Accessibility → VoiceOver).
- Amazon Fire: VoiceView (Settings → Accessibility → VoiceView) or TalkBack on Android-based devices.

## Using the Mobile UI
1. Open: `/public/mobile/index.html` (or Add to Home Screen).
2. Dictate with the system mic (keyboard mic on iPhone / Fire).
3. Send to Agent: Double-tap. The page announces status and speaks the answer.
4. Speak Response: Replays the last answer.
5. Connect to Desktop: Opens the RDP profile (native client) or web session.

## One-tap Remote Desktop (RDP)
Native app (recommended):
- Install Microsoft Remote Desktop (iOS / Android). On Fire tablets, use Amazon Appstore version or a compatible RDP client.
- Tap Connect to Desktop (serves `public/rdp/desktop.rdp`) → the RD client opens and connects.

Web fallback:
- Use a Guacamole gateway (see `docker-compose.rdp.yml`). Link your mobile UI to `/guac/#/client/<id>` behind a reverse proxy.

## In-session accessibility
- Windows: enable NVDA or JAWS for spoken UI; increase display scaling.
- Linux: enable Orca.
- Prefer large targets and high contrast; avoid color-only cues. Keep audio feedback on.

## Siri Shortcut (iPhone)
Actions:
1. Dictate Text (ask “What should I ask the agent?”)
2. Get Contents of URL (POST `http://<server>:8000/api/agent`, JSON `{"input": Provided Input}`)
3. Get Dictionary Value → `output`
4. Speak Text
Phrase: “Hey Siri, Ask Agent”.

## Fire tablet tips
- Use VoiceView tutorial to learn gestures.
- If Microsoft RD Client isn’t available in Appstore, use a compatible RDP client or the web gateway.

