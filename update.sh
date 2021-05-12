#!/bin/bash

git pull

supervisorctl restart api.plotter
supervisorctl restart api.nas

