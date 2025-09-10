# ZIRCON

## Description
Automation in railway signaling projects. Possible train movements, interlocking requirements, delay timings and incompatible movements are automatically obtained from signaling diagrams (i.e. automatic generation of PEE and Incompatibilities from DS/DSA data). Rapid design iterations in the project phase are enabled, accelerating delivery and enhancing optimization, while also improving safety.

## ZIRCON Layout Topography File (.zlt)

### General rules
1. The filename should be the stations abbreviation, for ease of use
2. All caps
3. Every line starts with a keyword (**BLK**, **NDZ**, **SEC**, **NDE**, **PNT**, **SIG**, **SWP**)
4. No trailing or leading spaces
5. No empty lines, except for last line
6. Tabs should used before keywords to denote dependency between encoded elements
7. Keyword arguments are separated by whitespaces
   
### Encoding a block
1. Write keyword **BLK**
2. Write the block's label after the keyword (three letters or three letters followed by one number character). If the number in the label is odd, it is assumed that the block has an ascending normal direction, and vice versa. 
3. If the block has an associated signal, encode it on the next line using the signal specific keywords (**SIG** or **SWP**)

### Encoding an area without train detection (singularly connected to the area with train detection)
1. Write keyword **NDZ**
2. Write the label of the no-detection-zone after the keyword
3. If the no detection zone has an associated signal, encode it on the next line using the signal specific keywords (**SIG** or **SWP**)

### Encoding a section
1. Write keyword **SEC**
2. Write the section's label after the keyword
3. If the section contains a double-junction-switch, write **TJD** after the section's label
4. If the section does not possess train detection (area without train detection not singularly connected to the area with train detection), write **NDZ** after the section's label or after **TJD**

### Encoding a node
1. Write keyword **NDE**
2. Write the node's index after the keyword
3. If there is an element connected to the node, write the label of that element after the node's index
4. If the section containing the encoded node contains a single-junction-switch, and the node can not be crossed by transits that also cross section branches, write **-** after the label of the connected element
* Note 1: A node is always associated with a section. The association is made with the section encoded immediatly before the node
* Note 2: The index of a node is an uppercase letter found by negativelly rotating an imaginary axis over the section containing the relevant node. The first node to be intersectid by the imaginary axis has index "A", and the next intercepted nodes are assigned the following alphabet's letters
  
### Encoding a signal
1. Write keyword **SIG** if the signal has no associated pedal, otherwise write keyword **SWP**
2. Write the signal's label after the keyword. If the signal is for circulation movements, the label should contain "S". If the signal is for shunt movements, the label should contain "M". If the signal is for circulation and shunt movements, the label should contain "S" and "M". If the signal is a shunting limit indicator, the signal label should be "M"
3. If the signal is for circulation movements but it can not originate main movements (i.e. the signal only has red and white beams), write __*__ after the signal's label
* Note 1: A signal is always associated with a node, a block, or a no-detection-zone. The association is made with the node, block, no-detection-zone encoded immediatly before the signal
* Note 2: A signal is associated with the element on to which it filters an incoming movement, even if it phisically lies on another element. The node with which the signal is associated is the node that would first be crossed by the incoming movement filtered by the signal. If the signal is associated with a block or singularly connected no-detection-zone, it is not associated with a node since these elements do not possess explicit nodes (they only have one connection, hence one node, hence the signal is associated with the connection of that element with the area with train detection)

### Encoding a switch or derailer
1. Write keyword **SWI**
2. Write the switch's label after the keyword. If the switch is a derailer, the label must contain "C"
* Note 1: A switch is always associated with a node. The association is made with the node encoded immediatly before the switch
* Note 2: If a transit through a section's node requires a switch on that section to be set in the reverse position, then that switch is associated with that node



















