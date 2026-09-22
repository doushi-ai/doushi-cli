# ✦ Doushi AI CLI (`doushi` / `dsh`)

[![PyPI Version](https://img.shields.io/badge/pypi-v0.1.0-blue.svg)](https://pypi.org/project/doushi-cli/)
[![Python Versions](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://pypi.org/project/doushi-cli/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Doushi Platform](https://img.shields.io/badge/Platform-Doushi.ai-cyan.svg)](https://doushi.ai)

**The official command-line interface for [Doushi.ai](https://doushi.ai)** — empowering developers, data scientists, and hackers to build, train, inspect, and deploy autonomous machine learning models directly from their terminal.

---

## ✨ Features

- ⚡ **Zero-Boilerplate ML**: Go from raw datasets (`.parquet`, `.xls`, `.xlsx`, `.json`, `.csv`, `.tsv`) to production-ready models in a single command.
- 🔒 **Security-First Auth**: AWS CLI-style credential management (`~/.doushi/credentials` with strict `0600` permissions).
- 🛡️ **Pre-Flight Limit Checks**: Validates dataset integrity and file limits locally before uploading.
- 🔄 **Real-Time Streaming**: Watch the autonomous self-healing agent loop live in your terminal.
- 🚀 **Live Inference & Pipes**: Predict via inline JSON, batch CSV files, or standard input streams (`cat data.csv | doushi predict <id>`).
- 📦 **No Vendor Lock-In**: Export raw scikit-learn/XGBoost training code, `model.pkl`, FastAPI microservice, and Dockerfile with `doushi export`.

---

## 📦 Installation

Install via `pip`:
```bash
pip install doushi-cli
```

Or run instantly without installing using `pipx`:
```bash
pipx run doushi demo
```

*(Both `doushi` and `dsh` are available as CLI aliases)*

---

## 🚀 Quickstart in 60 Seconds

### 1. Authenticate your terminal
```bash
doushi configure
```
*(Prompts for your API key from [app.doushi.ai](https://app.doushi.ai))*

### 2. Try the 30-second instant demo
```bash
doushi demo
```
*(Trains an autonomous model on a sample customer churn dataset and shows live performance metrics)*

### 3. Train on your own dataset
```bash
doushi train ./my_dataset.csv --goal "Predict customer churn probability"
```

---

## 📖 Command Reference

### Authentication
```bash
doushi configure       # Set up API Key & verify credentials
doushi whoami          # View active organization, plan tier, and project quotas
doushi logout          # Remove stored local credentials
```

### Model Training & Projects
```bash
# Upload dataset and train with autonomous agent
doushi train ./dataset.csv --goal "Predict house sale prices"

# List all organization projects and best metrics
doushi projects list

# Inspect detailed model parameters, KPIs, and dataset preview
doushi projects view <project_id>

# Delete a project
doushi projects delete <project_id>
```

### Predictions & Inference
```bash
# 1. Predict with single inline JSON record
doushi predict <project_id> --data '{"age": 32, "tenure": 12, "balance": 4500.0}'

# 2. Batch predict from a test CSV file
doushi predict <project_id> --file ./test_records.csv --output ./predictions.csv

# 3. Unix standard input piping
cat records.csv | doushi predict <project_id> | jq '.predictions[]'
```

### Observability & Code Export
```bash
# Stream real-time agent execution & self-healing sandbox logs
doushi logs <project_id> -f

# Export standalone model bundle (model.pkl + FastAPI + Dockerfile)
doushi export <project_id> --out ./model-bundle/
```

---

## 📂 Exported Model Bundle Structure

Running `doushi export <project_id>` gives you everything you need to run completely independent of Doushi:

```text
model-bundle/
├── model.pkl            # Pretrained model weights
├── pipeline.py          # Complete scikit-learn / XGBoost training script
├── requirements.txt     # Locked dependencies
├── serve.py             # FastAPI REST microservice
├── Dockerfile           # Production container
└── README.md            # Local deployment instructions
```

---

## 🛠️ Development & Contributing

### Local Setup
```bash
git clone https://github.com/doushi-ai/doushi-cli.git
cd doushi-cli

python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"
```

### Run Test Suite
```bash
python3 -m unittest discover -s tests
```

---

## 📄 License

Distributed under the [MIT License](LICENSE). See `LICENSE` for more information.

---

<p align="center">
  Built with ✦ by the <a href="https://doushi.ai">Doushi.ai</a> Team
</p>
