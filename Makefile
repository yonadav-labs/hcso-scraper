.PHONY: build-cron build-web run-cron run-web

build-cron:
	docker build -t gregorywhite/scraper-cron -f Dockerfile-cron .

build-web:
	docker build -t gregorywhite/scraper-web -f Dockerfile-web .

run-cron:
	docker run --rm -d --name scraper-cron gregorywhite/scraper-cron

run-web:
	docker run --rm -d --name scraper-web -p 8000:8000 gregorywhite/scraper-web

dev:
	docker run --rm -it -v `pwd`:/app -p 8000:8000 gregorywhite/scraper-web sh
