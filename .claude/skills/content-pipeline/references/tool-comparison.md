# Tool Quick-Reference Comparison

## Video Generation Tools

### LTX-2.3 (Local — ComfyUI)
- **Cost**: Free (local GPU)
- **Max duration**: 20 seconds/clip
- **Resolution**: Up to 1440p native (4K via upscaler)
- **Audio**: Synchronized audio generation
- **FPS**: 24, 25, 48, 50
- **Camera LoRAs**: Yes (Dolly, Jib, Static + CivitAI community)
- **Image-to-Video**: Yes
- **Video Extend**: Yes (last-frame continuation)
- **VRAM**: 32GB minimum (RTX 5090 compatible)
- **Best for**: Free generation, LoRA customization, rapid local iteration
- **CFG**: 3.0-3.5 recommended

### Veo 3.1 (Cloud — Google)
- **Cost**: $0.15-0.75/second depending on tier
- **Max duration**: 8 seconds/clip, ~148s via scene extension
- **Resolution**: 720p, 1080p, 4K
- **Audio**: Best-in-class native audio (dialogue, SFX, music, ambient)
- **FPS**: 24
- **Reference images**: Up to 3 (Standard/Full tier only)
- **Scene extension**: Up to 20 extensions (7s each)
- **Best for**: Character consistency, native audio, product videos with sound
- **Access**: Gemini API, Vertex AI, Gemini App

### Sora 2 / Sora 2 Pro (Cloud — OpenAI)
- **Cost**: Credit-based (16-40 credits/second depending on resolution)
- **Max duration**: 4-12s (sora-2), 10-25s (sora-2-pro)
- **Resolution**: 720p (sora-2), 720p/1080p (sora-2-pro)
- **Audio**: Native synchronized audio
- **FPS**: Cinematic
- **Character consistency**: None (no memory between generations)
- **Best for**: Photorealism, narrative storytelling, cinematic quality
- **Access**: ChatGPT Plus ($20/mo) or Pro ($200/mo)

## Image Generation Tools

### Nano Banana 2 (Google)
- **Cost**: ~$0.03/call via third-party, variable via official API
- **Resolution**: Up to 4K
- **Character consistency**: Up to 5 characters
- **Object consistency**: Up to 14 objects
- **Text rendering**: Excellent
- **Speed**: 2-5x faster than predecessors (varies by resolution)
- **Best for**: Product photography, e-commerce sets, character references
- **Responds well to**: Photography terminology (cameras, lenses, film stocks)

### ChatGPT Image Gen (GPT-4o)
- **Cost**: Included in ChatGPT subscription; API pricing: Low ~$0.01, Medium ~$0.04, High ~$0.17 per image
- **Resolution**: Standard
- **Character consistency**: None built-in
- **Text rendering**: Good
- **Speed**: Standard
- **Best for**: Quick concepts, conversational editing, storyboard frames
- **Responds well to**: Natural language, conversational direction

## Decision Matrix

| Need | Choose |
|------|--------|
| Free video generation | LTX-2.3 |
| Best audio in video | Veo 3.1 |
| Character consistency across video shots | Veo 3.1 (with references) |
| Camera LoRA control in video | LTX-2.3 |
| Fastest video iteration | LTX-2.3 (local) |
| Longest single continuous video | Veo 3.1 (148s via extension) |
| Product photography set | Nano Banana 2 |
| Quick concept image | ChatGPT |
| Character reference sheet | Nano Banana 2 |
| Highest photorealism video | Sora 2 or Veo 3.1 |
| Privacy-sensitive content | LTX-2.3 (fully local) |

## Platform-Specific Recommendations

### TikTok Content
- Aspect: 9:16
- Duration: 15-60s
- Video tool: LTX-2.3 (free, fast) or Veo 3.1 (with audio)
- Energy: High — fast movements, crash zooms
- Hook: First 0.5s must grab attention

### Instagram Reels
- Aspect: 9:16
- Duration: 15-90s
- Video tool: Veo 3.1 (polished, audio) or Sora 2 (cinematic)
- Energy: Medium-high — polished and aesthetic
- Style: Clean, well-lit, aspirational

### Product Ads
- Aspect: 16:9 or 1:1
- Duration: 15-30s
- Video tool: LTX-2.3 (LoRA control) or Veo 3.1 (audio)
- Image tool: Nano Banana 2 (product references)
- Energy: Medium — elegant, deliberate

### B-Roll Package
- Aspect: 16:9
- Duration: 5-10s per clip, 8-12 clips
- Video tool: LTX-2.3 (free, varied LoRAs)
- Energy: Low-medium — smooth, cinematic
- Variety: Mix wide/medium/close, different movements
