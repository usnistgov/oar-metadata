# URL decoding library
#
# This implementation comes from https://rosettacode.org/wiki/URL_decoding#jq
# (modified 8 April 2018) and is made available under GNU Free Documentation
# License 1.2.

# Emit . and stop as soon as "condition" is true.
#
# Input:     any 
# Output:    same as input
# condition: conditional code 
# next:      filter to apply if condition is false
# 
def until(condition; next):
  def u: if condition then . else (next|u) end;
  u;

# interpret a string as a number in some base system
#
# Input:     string
# Output:    number
#
def to_i(base):
  explode
  | reverse
  | map(if 65 <= . and . <= 90 then . + 32  else . end)   # downcase
  | map(if . > 96  then . - 87 else . - 48 end)  # "a" ~ 97 => 10 ~ 87
  | reduce .[] as $c
      # base: [power, ans]
      ([1,0]; (.[0] * base) as $b | [$b, .[1] + (.[0] * $c)]) | .[1];

def hex2utf8(shift; off):
  [to_i(16)-off+((shift|to_i(16))*64)] | implode;

def hex2utf8(shift):
  hex2utf8(shift; 128);

def hex2utf8:
  hex2utf8("0"; 0);

# replace all url-encodings (%XX) in an input string with their unencoded
# characters.  This decoder should be fully UTF-8 compliant, recognizing
# the %CX%XX pattern.  
#
# Input:  string
# Output: string
# 
def url_decode:
  .  as $in
  | length as $length
  | [0, ""]  # i, answer
  | until ( .[0] >= $length;
      .[0] as $i
      |  if $in[$i:$i+1] == "%"
         then
           if $in[$i+1:$i+2] == "C" and $in[$i+3:$i+4] == "%"
           then [ $i + 6, .[1] + ($in[$i+4:$i+6] | hex2utf8($in[$i+2:$i+3])) ]
           else [ $i + 3, .[1] + ($in[$i+1:$i+3] | hex2utf8) ]
           end
         else [ $i + 1, .[1] + $in[$i:$i+1] ]
         end)
  | .[1];   # answer

# replace url-encodings, including pluses (+), with their corresponding
# characters.  This is like url_encode, except that it also replaces each
# plus with a space.
#
# Input:  string
# Output: string
# 
def url_decode_plus:
  gsub("\\+"; " ") | url_decode 
;
