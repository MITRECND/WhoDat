WhoDat Project
==============

The WhoDat project is a front-end for whoisxmlapi data, or any whois data
living in a MongoDB. It integrates whois data, current IP resolutions and
passive DNS. In addition to providing an interactive, pivotable application
for analysts to perform research, it also has an API which will allow output
in JSON or list format.

WhoDat was originally written by [Chris Clark](https://github.com/Xen0ph0n).
The original implementation is in PHP and availble in this repository under
the [whodat](../blob/master/whodat) directory. The code was re-written from
scratch by [Wesley Shields](https://github.com/wxsBSD) and
[Murad Khan](https://github.com/mraoul) in Python, and is available under the
[pydat](../blob/master/pydat) directory.

The PHP version is left for those who want to run it, but it is not as full
featured or extensible as the Python implementation, and is not supported.

For more information on the PHP implementation please see the [readme](../blob/master/whodat/README.md). For more information on the Python impementation
please see the [readme](../blob/master/pydat/README.md).

License stuff: 

The PHP implementation is copyright Chris Clark, 2013. Contact him at
Chris@xenosys.org. The Python implementation is copyright The MITRE
Corporation, 2014. Both versions are licensed under the same license.

WhoDat is free software: you can redistribute it and/or modify it under the
terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

WhoDat is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with
WhoDat. If not, see http://www.gnu.org/licenses/.
