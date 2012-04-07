: 2dup ( a b -- a b a b ) over over ;
: 2drop ( a b -- ) drop drop ;
: nip ( a b -- b ) swap drop ;
: tuck ( a b -- b a b ) swap over ;
: r> ( R: a -- ) ( S: -- a ) r@ rdrop ;
