#!/bin/bash
mysqldump -u root -p jkilopqcv0968 db_fredshao_blog > `date + %Y%m%d`.db_fredshao_blog.sql
