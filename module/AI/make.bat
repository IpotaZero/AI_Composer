copy AI.py AI.pyx
cythonize -3 -a -i AI.pyx
ren AI.cp311-win_amd64.pyd AI.pyd
rm AI.pyx
pause