# Bachelor Thesis
![alt text](https://raw.githubusercontent.com/pheanex/BachelorThesis/master/Bilder/RWTH-Aachen-logo.png "RWTH Aachen") ![alt text](https://raw.githubusercontent.com/pheanex/BachelorThesis/master/Bilder/comsys-logo.png "ComSys RWTH") ![alt text](https://raw.githubusercontent.com/pheanex/BachelorThesis/master/Bilder/lancom-logo.png "LANCOM Systems")
## Title: Robust Link Selection and Channel Assignment for Centrally Managed Wireless Mesh Networks
## Abstract
Using a wireless backbone in a WDS can be tricky as performance decreases with increasing size due to interference, 
especially if channels and network topology are not selected carefully beforehand. 
Additionally network dissociations may occur easily if crucial links fail as redundancy is neglected.

Therefore we present an algorithm and its implementation which addresses this problem by finding a network topology and channel assignment 
that minimizes interference and thus allows a deployment to increase its throughput performance by utilizing more bandwidth in the local spectrum. 
Our evaluation results show an increase in throughput performance of up to 9 times or more compared to a baseline scenario where an optimization has not taken place
and only one channel for the whole network is used.
Furthermore our solution also provides a robust network topology which tackles the issue of network partition for single link failures by using survival paths.

We achieve this gain in performance by utilizing multi-radio Accesspoints and enhancing the DJP-algorithm for graphs by a scoring system combined with
a greedy channel assignment.

![alt text](https://github.com/pheanex/BachelorThesis/blob/master/Bilder/topo_chan_1_6_11_36_40_44.png?raw=true "Abstract network mesh") 

You can find the thesis here [thesis.pdf](https://github.com/pheanex/BachelorThesis/raw/master/Thesis/thesis.pdf)
