%chk=system.chk
%mem=10Gb
%nprocshared=4
#p b3lyp/6-311++G(d,2p) nosymm test polar=dipole

TITLE mol 

0 1
C 30.300025    1.272822    5.521261
H 31.238875    1.477919    6.033497
H 30.490014    0.653971    4.646496
H 29.846457    2.213110    5.210806
H 29.624628    0.752178    6.197940

