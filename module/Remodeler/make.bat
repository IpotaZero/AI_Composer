rem Remodeler.pyx
copy Remodeler.py Remodeler.pyx
cythonize -3 -a -i Remodeler.pyx
ren Remodeler.cp311-win_amd64.pyd Remodeler.pyd
pause