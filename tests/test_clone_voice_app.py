import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

# ensure project path is on sys.path
PROJECT_ROOT = Path(__file__).parent.parent / "clonar voz"
sys.path.insert(0, str(PROJECT_ROOT))

# import scripts after adjusting path
import train
import synth

from fastapi.testclient import TestClient

# import web app
from web import app as web_app


def test_train_no_data(capsys, tmp_path, monkeypatch):
    # point data_dir to empty temp directory
    monkeypatch.setattr(train, 'data_dir', str(tmp_path / 'data'))
    monkeypatch.setattr(train, 'os', os)
    # run main
    train.main()
    captured = capsys.readouterr()
    assert "No hay datos" in captured.out


def test_synth_no_model(tmp_path):
    # ensure models folder does not exist
    models_dir = tmp_path / 'models'
    if models_dir.exists():
        shutil.rmtree(models_dir)
    # call synth main via subprocess to capture printed message
    result = subprocess.run([sys.executable, str(PROJECT_ROOT / 'synth.py'), 'hola', str(tmp_path / 'out.wav')], capture_output=True, text=True)
    assert "No hay modelo local" in result.stdout


def create_dummy_wav(path: Path):
    import numpy as np
    import soundfile as sf
    data = np.zeros(16000, dtype='float32')
    sf.write(str(path), data, 16000)


def test_web_endpoints(tmp_path, monkeypatch):
    # configure directories under tmp_path
    data_dir = tmp_path / 'data'
    recordings = data_dir / 'recordings'
    data_dir.mkdir()
    recordings.mkdir()

    monkeypatch.setattr(web_app, 'data_dir', str(data_dir))
    monkeypatch.setattr(web_app, 'recordings_dir', str(recordings))
    monkeypatch.setattr(web_app, 'transcript_path', str(data_dir / 'transcripts.txt'))

    client = TestClient(web_app)

    # GET index page
    resp = client.get('/')
    assert resp.status_code == 200
    assert '<h1>Clonador de voz</h1>' in resp.text

    # Upload dummy wav
    wav_path = tmp_path / 'dummy.wav'
    create_dummy_wav(wav_path)
    with open(wav_path, 'rb') as f:
        resp = client.post('/upload', data={'text': 'hola'}, files={'file': ('dummy.wav', f, 'audio/wav')})
    assert resp.status_code == 303
    # check transcripts file updated
    with open(data_dir / 'transcripts.txt', 'r', encoding='utf-8') as t:
        content = t.read().strip()
    assert 'dummy.wav|hola' in content

    # synthesize endpoint: monkeypatch subprocess call to avoid real TTS
    async def fake_subprocess(cmd, *args, **kwargs):
        class P:
            async def communicate(self):
                # create dummy output file if command contains "out.wav"
                out = data_dir / 'output.wav'
                with open(out, 'wb') as w:
                    w.write(b'RIFF')
                return (b'', b'')
        return P()

    monkeypatch.setattr(web_app, 'asyncio', __import__('asyncio'))
    monkeypatch.setattr(web_app.asyncio, 'create_subprocess_shell', fake_subprocess)

    resp = client.post('/synthesize', data={'text': 'test'})
    assert resp.status_code == 200
    assert resp.headers['content-type'] == 'audio/wav'
    assert resp.content.startswith(b'RIFF')
