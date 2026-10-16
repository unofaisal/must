# Day 1 (Oct 12)

I built this with OpenCode, and the first thing I did was not write code. I gave it a lot of context on what I was trying to do and let it ask me clarifying questions until we agreed on the goal, the limits and what "done" meant. Only then did we write the intent and the directive.

From that, the first working version was small on purpose: a keyword classifier with six intents, one template reply per intent, a command-line runner and 12 sample messages. Rules first because I could read them and test them offline, with no key and no network.

The model wrote tests alongside the code and ran them itself. I read the results instead of re-running things by hand.

What broke: with "first matching rule wins", a message that mentioned two things went to the wrong group. I had to order the rules carefully (withdrawal and technical problems before the generic labels) to get sensible results. That was my first sign that one label per message was the wrong shape.
