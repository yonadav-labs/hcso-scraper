.PHONY: build-cron build-web run-cron run-web

build-cron:
	docker build -t gregorywhite/scraper-cron -f Dockerfile-cron .

build-web:
	docker build -t gregorywhite/scraper-web -f Dockerfile-web .

run-cron:
	docker run -d --name scraper-cron --restart=unless-stopped gregorywhite/scraper-cron

run-web:
	docker run -d --name scraper-web --restart=unless-stopped -p 80:8000 gregorywhite/scraper-web

dev:
	docker run --rm -it -v `pwd`:/app -p 8000:8000 gregorywhite/scraper-web sh
