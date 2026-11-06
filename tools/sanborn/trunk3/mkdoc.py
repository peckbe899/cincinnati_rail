import sys
src = open(sys.argv[1]).read(); tail = open(sys.argv[2]).read()
src = src.replace('Status: installed in the Mill Creek Deck page as Version 127 (26 October 2026);', 'Status: installed in the Mill Creek Deck page as Version 127 (26 October 2026), extended north of Mitchell to the borders in Version 128;')
src = src[:src.index('## Still to do')] + tail
open(sys.argv[3], 'w').write(src)
