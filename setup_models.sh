#!/bin/bash
# Download required NLP models for the brand management tool.

set -e

echo "=== Downloading NLP models ==="

# fastText language detection model
if [ ! -f "lid.176.ftz" ]; then
    echo "Downloading fastText language detection model..."
    curl -L -o lid.176.ftz https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz
    echo "✓ fastText model downloaded"
else
    echo "✓ fastText model already exists"
fi

# Pre-download HuggingFace models (they cache automatically)
echo "Pre-downloading HuggingFace models..."

python3 -c "
from transformers import pipeline
print('Loading XLM-RoBERTa sentiment model...')
pipeline('sentiment-analysis', model='cardiffnlp/twitter-xlm-roberta-base-sentiment-multilingual')
print('✓ Sentiment model cached')
"

python3 -c "
from sentence_transformers import SentenceTransformer
print('Loading MiniLM embedding model...')
SentenceTransformer('all-MiniLM-L6-v2')
print('✓ Embedding model cached')
"

echo ""
echo "=== All models ready ==="
