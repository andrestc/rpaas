# Copyright 2016 rpaas authors. All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

.PHONY: test deps

clean_pycs:
	find . -name \*.pyc -delete

run: deps
	python ./rpaas/api.py

worker: deps
	celery -A rpaas.tasks worker

flower: deps
	celery flower -A rpaas.tasks

start-consul: stop-consul
	consul agent -ui -server -bind 127.0.0.1 -bootstrap-expect 1 -data-dir /tmp/consul -config-file etc/consul.conf -node=rpaas-test &
	while ! consul info; do sleep 1; done

stop-consul:
	-consul leave
	rm -rf /tmp/consul

test: start-consul ci-test

ci-test: clean_pycs deps redis-sentinel-test
	@python -m unittest discover
	@flake8 --max-line-length=120 .

deps:
	pip install -e .[tests]

coverage: deps
	rm -f .coverage
	coverage run --source=. -m unittest discover
	coverage report -m --omit=test\*,run\*.py

kill-redis-sentinel-test:
	-redis-cli -a mypass -p 51115 shutdown
	-redis-cli -a mypass -p 51114 shutdown
	-redis-cli -a mypass -p 51113 shutdown
	-redis-cli -p 51112 shutdown
	-redis-cli -p 51111 shutdown

redis-sentinel-test: kill-redis-sentinel-test copy-redis-conf
	redis-sentinel /tmp/redis_sentinel_test.conf --daemonize yes || redis-server /tmp/redis_sentinel_test.conf --sentinel --daemonize yes; sleep 1
	redis-sentinel /tmp/redis_sentinel2_test.conf --daemonize yes || redis-server /tmp/redis_sentinel2_test.conf --sentinel --daemonize yes; sleep 1
	redis-server /tmp/redis_test.conf --daemonize yes; sleep 1
	redis-server /tmp/redis_test2.conf --daemonize yes; sleep 1
	redis-server /tmp/redis_test3.conf --daemonize yes; sleep 1
	redis-cli -p 51111 info | grep sentinel

copy-redis-conf:
	@cp tests/testdata/sentinel_conf/*.conf /tmp
