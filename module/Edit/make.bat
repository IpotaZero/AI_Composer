copy Edit.py Edit.pyx
cythonize -3 -a -i Edit.pyx
ren Edit.cp311-win_amd64.pyd Edit.pyd
rem Edit.pyx
pause