rem ComIII.pyx
copy ComIII.py ComIII.pyx
cythonize -3 -a -i ComIII.pyx
ren ComIII.cp311-win_amd64.pyd ComIII.pyd
pause