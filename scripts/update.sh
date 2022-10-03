export $(grep -v '^#' .env | xargs)

git pull --rebase

python3 pull_db.py

git add ../content/*
git commit -m 'Auto Sync with Notion'"

git push
