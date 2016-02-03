#!/bin/bash

# setup.sh script template

function installp
{
	cp ${mysqlmerge_bin[0]} ${mysqlmerge_bin[1]}
   chmod a+x ${mysqlmerge_bin[1]}
   
	return 0
}

function uninstallp
{
	rm ${mysqlmerge_bin[1]}
	
	return 0
}

function __main__
{
	# usage report
	declare -r USAGE="usage: bash setup.sh install | uninstall"
	
	# add any other constants or setup variables
   local mysqlmerge_bin=(mysqlmerge.py /usr/local/bin/mysqlmerge)
   
	if [ $# -eq 0 ]; then
		echo $USAGE
		exit 1
	fi
	
	case "$1" in
		"install"   )
			if ! installp; then
				exit 1
			fi
			;;
		"uninstall" )
			if ! uninstallp; then
				exit 1
			fi
			;;
		* )
			echo $USAGE
			exit 1
	esac
	
	exit 0
}

__main__ "$@"

