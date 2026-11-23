# Pitch Elo · 3 minutos

[Vídeo MP4](elo-pitch-3min.mp4) · [Narração MP3](narracao-elo.mp3) · [Roteiro](narracao.txt)

1920×1080, 30 fps, duração exata de 180 segundos. Montagem de capturas reais da aplicação com dados sintéticos, não uma gravação contínua de cliques. Narração ElevenLabs, voz Caio / Eleven Multilingual v2, gerada com autorização do titular da conta. Nenhuma credencial ou screenshot da conta do provedor está incluído.

## Editar e renderizar

O projeto usa HyperFrames 0.9.83; requer Node.js, Chrome e FFmpeg. Use o launcher da skill HyperFrames instalada ou os comandos do package.json conforme seu ambiente. `index.html` reúne cenas em `compositions/`, telas em `assets/screens/` e áudio em `assets/narracao.wav`. `python3 build_video.py` regenera os HTMLs e substitui edições manuais desses arquivos.

As telas são evidências da versão demonstrada; futuras mudanças no aplicativo não atualizam automaticamente o vídeo. A síntese de novas vozes exige acesso próprio ao provedor; os áudios já gerados estão incluídos. Não há publicação automática.

Veja SPEC.md e REVIEW.md para decisões de montagem e limites da verificação.
