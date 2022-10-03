export $(grep -v '^#' .env | xargs)

for file in $(python3 pull_db.py)
do
	#git pull --rebase
	echo "git commit -m 'Auto Sync \"${file#markdown/}\" from Notion' ./$file"
	#git push
done
