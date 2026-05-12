SHELL := /bin/bash
PIP_DEPS = -r requirements.txt coverage

site: generate-blog
	./makesite.py

LOOPS = 10
generate-blog: ## Generate random blogs
	set -ex
	for ((i=1;i<=${LOOPS};i++)) do python3 ./scripts/generate.py > content/blog/$(shell date -I)-$$i.md; done

serve: site
	if python3 -c 'import http.server' 2> /dev/null; then \
	    echo Running Python3 http.server ...; \
	    cd _site && python3 -m http.server; \
	elif python -c 'import http.server' 2> /dev/null; then \
	    echo Running Python http.server ...; \
	    cd _site && python -m http.server; \
	elif python -c 'import SimpleHTTPServer' 2> /dev/null; then \
	    echo Running Python SimpleHTTPServer ...; \
	    cd _site && python -m SimpleHTTPServer; \
	else \
	    echo Cannot find Python http.server or SimpleHTTPServer; \
	fi

venv: FORCE
	python3 -m venv ~/.venv/makesite
	echo . ~/.venv/makesite/bin/activate > venv
	. ./venv && pip install $(PIP_DEPS)

test: FORCE
	. ./venv && python -m unittest -bv

coverage:
	. ./venv && coverage run --branch --source=. -m unittest discover -bv; :
	. ./venv && coverage report -m
	. ./venv && coverage html

clean:
	find . -name "__pycache__" -exec rm -r {} +
	find . -name "*.pyc" -exec rm {} +
	rm -rf .coverage htmlcov

FORCE:
