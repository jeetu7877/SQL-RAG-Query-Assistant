from types import SimpleNamespace

from app.ai.vanna_service import GeminiEmbedding


def test_gemini_embedding_batches_and_returns_vectors():
    calls = []

    class FakeModels:
        def embed_content(self, model, contents, config):
            calls.append((model, len(contents), config["output_dimensionality"]))
            return SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1] * 768) for _ in contents])

    emb = GeminiEmbedding.__new__(GeminiEmbedding)
    emb.client = SimpleNamespace(models=FakeModels())
    emb.model = "gemini-embedding-001"
    out = emb(["t"] * 120)
    assert len(out) == 120 and len(out[0]) == 768
    assert [c[1] for c in calls] == [50, 50, 20]
