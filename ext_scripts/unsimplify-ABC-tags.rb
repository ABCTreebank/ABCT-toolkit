data = gets(nil)
         .gsub(%r|``_([A-Za-z]+)''|, '<\1/\1>\\<\1/\1>')
         .gsub(%r|([A-Za-z]+)''|, '<\1/\1>')
         .gsub(%r|``([A-Za-z]+)|, '<\1\\\\\1>')
         .gsub(%r|VP([a-z]+)|, '<PPs\\\\S\1>')
         # .gsub(%r|\(([<>A-Za-z\\/]+) |, '(<\1> ')
         # .gsub(%r|<([A-Za-z]+)> |, '\1 ')
         # .gsub(%r|<<([A-Za-z\\/]+)>> |, '<\1> ')

puts data 
