#!/bin/bash
export PYTHONHOME=/apps/nuke/Nuke15.0v4
export PYTHONPATH=$PYTHONPATH:'/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2:/tools/packages/nkt_api/1.0.0/platform-linux/arch-x86_64/os-rocky-9.2/python'
/apps/nuke/Nuke15.0v4/Nuke15.0 -t "/home/chandru/tmp/roto_packaging//roto_package_one.py"
