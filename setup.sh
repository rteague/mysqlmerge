#!/bin/bash

# setup.sh script template

function installp
{
	# add install code
	
	return 0
}

function uninstallp
{
	# add uninstall code
	
	return 0
}

function __main__
{
	# usage report
	declare -r USAGE="usage: bash setup.sh install | uninstall"
	
	# add any other constants or setup variables
   local _mysqlmerge_bin=(mysqlmerge.py /usr/local/bin/mysqlmerge)
   
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

