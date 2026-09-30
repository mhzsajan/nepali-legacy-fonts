"""What does each number mean, on each version of the inventory?"""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.stdout.reconfigure(encoding="utf-8")
import letter_sheet as LS

print("CURRENT inventory (%d letters):" % len(LS.INVENTORY))
for n in range(55, 68):
    g, ch, needs = LS.BY_NUMBER[n]
    print("   %3d  %-24s %r%s" % (n, g, ch, "  [chromium]" if needs else ""))

print()
print("group ranges now:")
for g, chars in LS.GROUPS:
    ns = [n for n, gg, _c, _x in LS.INVENTORY if gg == g]
    print("   %-28s %3d..%-3d  (%d)" % (g, ns[0], ns[-1], len(ns)))

print()
print("the consonant list, in order, with its number:")
n = 24
for ch in LS.CONSONANTS:
    n += 1
    mark = "   <-- no key in the Preeti table" if ch == "ळ" else ""
    print("   %3d  %s%s" % (n, ch, mark))

print()
print("count:", len(LS.CONSONANTS), "consonants")
print("standard varga order ends: ... स ह ळ = 34 entries")
print()
print("OLD inventory (the 89-cell sheet) had क्ष and ज्ञ INSIDE the consonant")
print("string, so they were split into separate cells by codepoint:")
old = "कखगघङचछजझञटठडढणतथदधनपफबभमयरलवशषसहळक्षज्ञ"
n = 24
for ch in old[33:]:
    n += 1
    print("   %3d  %r" % (n, ch))
