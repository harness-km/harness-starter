# Agent Harness Engineering — starter repository

Your copy of this repository is where your course work lives. Course site: https://course.krishnamohan.co

## Start here (Week 0)

1. Click **Use this template → Create a new repository** (top right of this page) to make your own copy. A private repository is fine.
2. Follow the Week 0 page on the course site: API key in Colab Secrets, spend limit, `week-00/setup.ipynb`.
3. Once, open your copy in a Codespace (**Code → Codespaces → Create codespace**) and run:
   ```
   git status
   make test
   make catch-up WEEK=00
   ```
   Then commit anything you changed and delete the Codespace. Week 7 starts with a fresh one.

## What is where

| Folder | What it holds |
| --- | --- |
| `week-00/` … `week-05/` | The weekly lab notebooks (Weeks 1–6 run in Google Colab) |
| `course-tools/` | The course helper package: dataset generator, fake model for offline self-checks, resource meter, self-checks |
| `solutions/` | Reference solutions, published after each week closes |
| `tests/` | `make test` |
| `scripts/catch_up.py` | `make catch-up WEEK=nn` (from Week 7) |

## Ground rules

- **Synthetic data only.** Never put real supplier, customer or company data in this repository, a notebook or a question.
- **No keys in code.** API keys live in Colab Secrets or Codespaces secrets, never in a notebook, a file, a screenshot or Git history. If one leaks, rotate it first.
- **Stuck?** Your pod first, then the course chatbot, then GitHub Discussions (use the template: what you ran, what you expected, the full error).
