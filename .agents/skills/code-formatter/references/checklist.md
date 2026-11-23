# Code Formatter Checklist

Run it before calling a formatting pass done.

- [ ] Every wrapped parameter list is followed by a blank line before the body
- [ ] No control-flow exit shares a line with its condition
- [ ] Blank lines mark the try, the async hand-off and the terminating call as distinct beats
- [ ] Every comment sits above the line it describes
- [ ] Every doc comment sits directly on its declaration, with no tag wrapped onto a second line
- [ ] No two consecutive blank lines inside a function body
- [ ] Fluent chains break before each dot, unless a formatter owns line breaking in the project
- [ ] Single-expression bodies were left on one line
- [ ] The file was already in this style, or the user asked for the conversion
