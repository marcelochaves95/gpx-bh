# Mapa BH
Ferramenta para gerar GPX de bairros de Belo Horizonte.

![](assets/bairros.png)

## Versão web (recomendada)
App estático (web/mobile) hospedado no GitHub Pages — sem instalação:

**https://marcelochaves95.github.io/mapa-bh**

Escolha um bairro, visualize o limite no mapa, baixe o `.gpx` ou abra direto no
gpx.studio. Em tempo de execução o site é 100% estático — não depende da API da PBH.

### Como os dados são gerados
Os dados **não** são versionados no repositório; eles são gerados no deploy:

1. `scripts/generate_data.py` busca os bairros na PBH e converte UTM → lat/lon,
   produzindo `docs/data/neighborhoods.json`.
2. `scripts/build_gpx.py` gera um `docs/data/gpx/<bairro>.gpx` por bairro (consumidos
   pelo botão "Abrir no gpx.studio").

Ambos os caminhos (`neighborhoods.json` e `gpx/`) estão no `.gitignore`.

### Publicar no GitHub Pages
A publicação é feita pelo workflow `.github/workflows/deploy.yml`. Em
**Settings → Pages**, defina a fonte (*Source*) como **GitHub Actions**. A cada push
na `main` (e mensalmente, para refrescar os dados) o workflow busca os dados da PBH,
gera os GPX e publica.

### Pré-visualizar localmente
Como os dados são gerados no deploy, gere-os antes de servir o site localmente:
```
pip install pyproj
python scripts/generate_data.py
python scripts/build_gpx.py
cd docs && python -m http.server 8000
```

## Versão desktop (Python/PyQt6)

### Instalação
1. Clone o repositório:
```
git clone https://github.com/marcelochaves95/mapa-bh.git
cd mapa-bh
```
2. Instale as dependências necessárias:
```
pip install -r requirements.txt
```

## Uso
1. Execute o script principal:
```
python main.py
```

2. Siga os passos na interface:
- Carregue a lista de bairros.
- Selecione um bairro.
- Gere e salve o arquivo GPX correspondente.

## Requisitos
- Python 3.9 ou superior.
- Dependências listadas em `requirements.txt`.
