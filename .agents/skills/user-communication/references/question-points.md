# Question Points

How to put a question or a decision in front of the user so it can be answered cold, and how to number it. Load this
file whenever a reply asks the user anything.

---

### Every point stands alone

A point carries everything needed to answer it cold: what the thing is, where it sits in the work, what differs
between the options, and what each one costs. Assume the user did not read what they did not reply to, and will not
remember even what they did reply to a round or two later. A point that needs the user to scroll up, open a file, or
read a ticket has failed. Pointing the user at one of those instead of explaining is the same failure.

Context a point needs is always restated, shortened if covered recently, never dropped. Only the report of a finished
result is said once.

A point that needs a decision has this shape, in this order:

1. The question first, in one line, so the user knows what the rest of the point is for.
2. The problem in plain words, short, skipping anything obvious.
3. The recommendation, why, and its minus, in two or three sentences, on a new line of its own after a blank line,
   so it stands out when the user scans for what to decide.

A point that needs no decision carries only the problem and the action, and says no decision is needed.

---

### Number only what needs the user

A number goes only to a point that asks the user something or needs the user's decision, and a numbered heading ends
in a question. A finished result, a status note, a plan outline, or an order of work gets a plain heading with no
number, or sits under the question it belongs to.

- Use one continuous sequence per conversation. Never restart at 1, never renumber, never open a fresh list at the
  end of a message, and set no upper limit.
- Give a number when the subject first appears. A finding, the question it raises, and the decision it needs are one
  subject and one number. Before assigning a new number, check whether the subject already has one or belongs under
  an existing number as a subpoint.
- Group related questions under one number with their shared context given once. Subpoints are 13.1 and 13.2, never
  letters. Put a horizontal rule between top-level numbers, never between subpoints.
- When the user replies about 13, answer as 13.
- Name the numbers you wait on in the `Waiting on` line of the status block, for example `your answer to 13, 14`.

---

### Worked example of a question point

```text
### 47. Where should the service read its public web address from?

47.1. Read the host from an environment variable, or write one fixed public hostname into the file?

The file /srv/orders/config/endpoints.yaml lists every download address a client uses to fetch an export. An
environment variable is a named value the operating system hands to a program when it starts. Three of the addresses
point at localhost, which means the machine the service runs on, so a client on any other machine gets connection
refused.

Recommendation: an environment variable named SERVICE_HOST, because one setting then fixes all three and nothing is
hardcoded. The minus is one more value to set in every deployment.

47.2. The three addresses also use different ports, 8080, 8081 and 8090. Keep them, or move to one shared port?

Recommendation: keep them for now, because changing ports also means changing the firewall rules. The minus is three
port numbers to remember instead of one.

Running: nothing

~~DONE: Read /srv/orders/config/endpoints.yaml~~
~~DONE: Trace which clients call the export addresses~~

**NOW: nothing, stopped until 47 is answered**

Next: change the addresses the way 47 decides
Then: rerun the export download test

Waiting on: your answer to 47
```
