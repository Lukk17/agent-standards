# Coding Standards Checklist

Run it before calling a change or a review done.

- [ ] Every name reveals intent, no single letters, no bare nouns for functions
- [ ] Public signatures annotated, locals typed the way the language's idiom says
- [ ] No magic number or string outside a named constant
- [ ] Guard clauses used instead of deep nesting
- [ ] No file past about 300 lines, and no divider banner or section-label comment
- [ ] No abstraction without a second real use case or a boundary that needs swapping or testing
- [ ] No merge of two blocks that only look alike and change for different reasons
- [ ] No swallowed exception, no empty catch, causes chained
- [ ] Errors returned in one structured shape, problem details on HTTP, no internal detail leaked
- [ ] Untrusted input validated once at the boundary into a typed value
- [ ] Business logic separable from framework, input and output, and storage
- [ ] State modelled as one of several named states, not a bag of flags
- [ ] Every feature flag has an owner and a removal date
- [ ] Every deliberate gap carries a ticketed task marker
- [ ] No comment states what the code already says, and the exported surface of a published library is documented
