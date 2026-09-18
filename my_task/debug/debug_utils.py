# 3rd Party Import
import ptvsd


def enable_debugger_server():
    # Enable Debugger
    ptvsd.enable_attach()


def test_debugger():
    """"""
    print("Welcome to Debugger Server")
