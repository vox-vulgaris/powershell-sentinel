Function Out-RandomCase
{
<#
.SYNOPSIS

HELPER FUNCTION :: Obfuscates any string or char[] by randomizing its case.

Invoke-Obfuscation Function: Out-RandomCase
Author: Daniel Bohannon (@danielhbohannon)
License: Apache License, Version 2.0
Required Dependencies: None
Optional Dependencies: None
 
.DESCRIPTION

Out-RandomCase obfuscates given input as a helper function to evade detection by simple IOCs and process execution monitoring relying solely on command-line arguments. For the most complete obfuscation all tokens in a given PowerShell script or script block (cast as a string object) should be obfuscated via the corresponding obfuscation functions and desired obfuscation levels in Out-ObfuscatedTokenCommand.ps1.

.PARAMETER InputValStr

Specifies the string to obfuscate.

.PARAMETER InputVal

Specifies the char[] to obfuscate.

.EXAMPLE

C:\PS> Out-RandomCase "String to have case randomized"

STrINg to haVe caSe RAnDoMIzeD

C:\PS> Out-RandomCase ([char[]]"String to have case randomized")

StrING TO HavE CASE randOmIzeD

.NOTES

This cmdlet is most easily used by passing a script block or file path to a PowerShell script into the Out-ObfuscatedTokenCommand function with the corresponding token type and obfuscation level since Out-ObfuscatedTokenCommand will handle token parsing, reverse iterating and passing tokens into this current function.
C:\PS> Out-ObfuscatedTokenCommand {Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green} 'Command' 3
This is a personal project developed by Daniel Bohannon while an employee at MANDIANT, A FireEye Company.

.LINK

http://www.danielbohannon.com
#>

    [CmdletBinding( DefaultParameterSetName = 'InputVal')] Param (
        [Parameter(Position = 0, ValueFromPipeline = $True, ParameterSetName = 'InputValStr')]
        [ValidateNotNullOrEmpty()]
        [String]
        $InputValStr,

        [Parameter(Position = 0, ParameterSetName = 'InputVal')]
        [ValidateNotNullOrEmpty()]
        [Char[]]
        $InputVal
    )
    
    If($PSBoundParameters['InputValStr'])
    {
        # Convert string to char array for easier manipulation.
        $InputVal = [Char[]]$InputValStr
    }

    # Randomly convert each character to upper- or lower-case.
    $OutputVal = ($InputVal | ForEach-Object {If((Get-Random -Minimum 0 -Maximum 2) -eq 0) {([String]$_).ToUpper()} Else {([String]$_).ToLower()}}) -Join ''

    Return $OutputVal
}

Function Out-ConcatenatedString
{
<#
.SYNOPSIS

HELPER FUNCTION :: Obfuscates any string by randomly concatenating it and encapsulating the result with input single- or double-quotes.

Invoke-Obfuscation Function: Out-ConcatenatedString
Author: Daniel Bohannon (@danielhbohannon)
License: Apache License, Version 2.0
Required Dependencies: None
Optional Dependencies: None
 
.DESCRIPTION

Out-ConcatenatedString obfuscates given input as a helper function to evade detection by simple IOCs and process execution monitoring relying solely on command-line arguments. For the most complete obfuscation all tokens in a given PowerShell script or script block (cast as a string object) should be obfuscated via the corresponding obfuscation functions and desired obfuscation levels in Out-ObfuscatedTokenCommand.ps1.

.PARAMETER InputVal

Specifies the string to obfuscate.

.PARAMETER Quote

Specifies the single- or double-quote used to encapsulate the concatenated string.

.EXAMPLE

C:\PS> Out-ConcatenatedString "String to be concatenated" '"'

"String "+"to be "+"co"+"n"+"c"+"aten"+"at"+"ed

.NOTES

This cmdlet is most easily used by passing a script block or file path to a PowerShell script into the Out-ObfuscatedTokenCommand function with the corresponding token type and obfuscation level since Out-ObfuscatedTokenCommand will handle token parsing, reverse iterating and passing tokens into this current function.
C:\PS> Out-ObfuscatedTokenCommand {Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green} 'CommandArgument' 3
This is a personal project developed by Daniel Bohannon while an employee at MANDIANT, A FireEye Company.

.LINK

http://www.danielbohannon.com
#>

    [CmdletBinding()] Param (
        [Parameter(Position = 0, Mandatory = $True)]
        [ValidateNotNullOrEmpty()]
        [String]
        $InputVal,
    
        [Parameter(Position = 1, Mandatory = $True)]
        [ValidateNotNullOrEmpty()]
        [Char]
        $Quote
    )

    # Strip leading and trailing single- or double-quotes if there are no more quotes of the same kind in $InputVal.
    # E.g. 'stringtoconcat' will have the leading and trailing quotes removed and will use $Quote.
    # But a string "'G'+'" passed to this function as 'G'+' will have all quotes remain as part of the $InputVal string.
    If($InputVal.Contains("'")) {$InputVal = $InputVal.Replace("'","`'")}
    If($InputVal.Contains('"')) {$InputVal = $InputVal.Replace('"','`"')}
    
    # Do nothing if string is of length 2 or less
    $ObfuscatedToken = ''
    If($InputVal.Length -le 2)
    {
        $ObfuscatedToken = $Quote + $InputVal + $Quote
        Return $ObfuscatedToken
    }

    # Choose a random percentage of characters to have concatenated in current token.
    # If the current token is greater than 1000 characters (as in SecureString or Base64 strings) then set $ConcatPercent much lower
    If($InputVal.Length -gt 25000)
    {
        $ConcatPercent = Get-Random -Minimum 0.05 -Maximum 0.10
    }
    ElseIf($InputVal.Length -gt 1000)
    {
        $ConcatPercent = Get-Random -Minimum 2 -Maximum 4
    }
    Else
    {
        $ConcatPercent = Get-Random -Minimum 15 -Maximum 30
    }
    
    # Convert $ConcatPercent to the exact number of characters to concatenate in the current token.
    $ConcatCount =  [Int]($InputVal.Length*($ConcatPercent/100))

    # Guarantee that at least one concatenation will occur.
    If($ConcatCount -eq 0) 
    {
        $ConcatCount = 1
    }

    # Select random indexes on which to concatenate.
    $CharIndexesToConcat = (Get-Random -InputObject (1..($InputVal.Length-1)) -Count $ConcatCount) | Sort-Object
  
    # Perform inline concatenation.
    $LastIndex = 0

    ForEach($IndexToObfuscate in $CharIndexesToConcat)
    {
        # Extract substring to concatenate with $ObfuscatedToken.
        $SubString = $InputVal.SubString($LastIndex,$IndexToObfuscate-$LastIndex)
       
        # Concatenate with quotes and addition operator.
        $ObfuscatedToken += $SubString + $Quote + "+" + $Quote

        $LastIndex = $IndexToObfuscate
    }

    # Add final substring.
    $ObfuscatedToken += $InputVal.SubString($LastIndex)
    $ObfuscatedToken += $FinalSubString

    # Add final quotes if necessary.
    If(!($ObfuscatedToken.StartsWith($Quote) -AND $ObfuscatedToken.EndsWith($Quote)))
    {
        $ObfuscatedToken = $Quote + $ObfuscatedToken + $Quote
    }
   
    # Remove any existing leading or trailing empty string concatenation.
    If($ObfuscatedToken.StartsWith("''+"))
    {
        $ObfuscatedToken = $ObfuscatedToken.SubString(3)
    }
    If($ObfuscatedToken.EndsWith("+''"))
    {
        $ObfuscatedToken = $ObfuscatedToken.SubString(0,$ObfuscatedToken.Length-3)
    }
    
    Return $ObfuscatedToken
}

Function Out-StringDelimitedAndConcatenated
{
<#
.SYNOPSIS

Generates delimited and concatenated version of input PowerShell command.

Invoke-Obfuscation Function: Out-StringDelimitedAndConcatenated
Author: Daniel Bohannon (@danielhbohannon)
License: Apache License, Version 2.0
Required Dependencies: Out-ConcatenatedString (located in Out-ObfuscatedTokenCommand.ps1), Out-EncapsulatedInvokeExpression (located in Out-ObfuscatedStringCommand.ps1), Out-RandomCase (located in Out-ObfuscatedToken.ps1)
Optional Dependencies: None
 
.DESCRIPTION

Out-StringDelimitedAndConcatenated delimits and concatenates an input PowerShell command. The purpose is to highlight to the Blue Team that there are more novel ways to encode a PowerShell command other than the most common Base64 approach.

.PARAMETER ScriptString

Specifies the string containing your payload.

.PARAMETER PassThru

(Optional) Outputs the option to not encapsulate the result in an invocation command.

.EXAMPLE

C:\PS> Out-StringDelimitedAndConcatenated "Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green"

(('Write-Ho'+'s'+'t'+' {'+'0'+'}'+'Hell'+'o Wor'+'l'+'d!'+'{'+'0'+'} -Foreground'+'Color G'+'ree'+'n; Writ'+'e-'+'H'+'ost {0}Obf'+'usc'+'a'+'tion R'+'o'+'ck'+'s!{'+'0} -Fo'+'reg'+'ro'+'undColor'+' '+'Gree'+'n')-F[Char]39) | Invoke-Expression

.NOTES

This cmdlet is most easily used by passing a script block or file path to a PowerShell script into the Out-ObfuscatedStringCommand function with the corresponding obfuscation level since Out-Out-ObfuscatedStringCommand will handle calling this current function where necessary.
C:\PS> Out-ObfuscatedStringCommand {Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green} 1
This is a personal project developed by Daniel Bohannon while an employee at MANDIANT, A FireEye Company.

.LINK

http://www.danielbohannon.com
#>

    [CmdletBinding()] Param (
        [Parameter(Position = 0)]
        [ValidateNotNullOrEmpty()]
        [String]
        $ScriptString,

        [Switch]
        $PassThru
    )

    # Characters we will substitute (in random order) with randomly generated delimiters.
    $CharsToReplace = @('$','|','`','\','"',"'")
    $CharsToReplace = (Get-Random -Input $CharsToReplace -Count $CharsToReplace.Count)

    # If $ScriptString does not contain any characters in $CharsToReplace then simply return as is.
    $ContainsCharsToReplace = $FALSE
    ForEach($CharToReplace in $CharsToReplace)
    {
        If($ScriptString.Contains($CharToReplace))
        {
            $ContainsCharsToReplace = $TRUE
            Break
        }
    }
    If(!$ContainsCharsToReplace)
    {
        # Concatenate $ScriptString as a string and then encapsulate with parentheses.
        $ScriptString = Out-ConcatenatedString $ScriptString "'"
        $ScriptString = '(' + $ScriptString + ')'

        If(!$PSBoundParameters['PassThru'])
        {
            # Encapsulate in necessary IEX/Invoke-Expression(s).
            $ScriptString = Out-EncapsulatedInvokeExpression $ScriptString
        }

        Return $ScriptString
    }
    
    # Characters we will use to generate random delimiters to replace the above characters.
    # For simplicity do NOT include single- or double-quotes in this array.
    $CharsToReplaceWith  = @(0..9)
    $CharsToReplaceWith += @('a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y','z')
    $CharsToReplaceWith += @('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z')
    $DelimiterLength = 3
    
    # Multi-dimensional table containing delimiter/replacement key pairs for building final command to reverse substitutions.
    $DelimiterTable = @()
    
    # Iterate through and replace each character in $CharsToReplace in $ScriptString with randomly generated delimiters.
    ForEach($CharToReplace in $CharsToReplace)
    {
        If($ScriptString.Contains($CharToReplace))
        {
            # Create random delimiter of length $DelimiterLength with characters from $CharsToReplaceWith.
            If($CharsToReplaceWith.Count -lt $DelimiterLength) {$DelimiterLength = $CharsToReplaceWith.Count}
            $Delim = (Get-Random -Input $CharsToReplaceWith -Count $DelimiterLength) -Join ''
            
            # Keep generating random delimiters until we find one that is not a substring of $ScriptString.
            While($ScriptString.ToLower().Contains($Delim.ToLower()))
            {
                $Delim = (Get-Random -Input $CharsToReplaceWith -Count $DelimiterLength) -Join ''
                If($DelimiterLength -lt $CharsToReplaceWith.Count)
                {
                    $DelimiterLength++
                }
            }
            
            # Add current delimiter/replacement key pair for building final command to reverse substitutions.
            $DelimiterTable += , @($Delim,$CharToReplace)

            # Replace current character to replace with the generated delimiter
            $ScriptString = $ScriptString.Replace($CharToReplace,$Delim)
        }
    }

    # Add random quotes to delimiters in $DelimiterTable.
    $DelimiterTableWithQuotes = @()
    ForEach($DelimiterArray in $DelimiterTable)
    {
        $Delimiter    = $DelimiterArray[0]
        $OriginalChar = $DelimiterArray[1]
        
        # Randomly choose between a single quote and double quote.
        $RandomQuote = Get-Random -InputObject @("'","`"")
        
        # Make sure $RandomQuote is opposite of $OriginalChar contents if it is a single- or double-quote.
        If($OriginalChar -eq "'") {$RandomQuote = '"'}
        Else {$RandomQuote = "'"}

        # Add quotes.
        $Delimiter = $RandomQuote + $Delimiter + $RandomQuote
        $OriginalChar = $RandomQuote + $OriginalChar + $RandomQuote
        
        # Add random quotes to delimiters in $DelimiterTable.
        $DelimiterTableWithQuotes += , @($Delimiter,$OriginalChar)
    }

    # Reverse the delimiters when building back out the reversing command.
    [Array]::Reverse($DelimiterTable)
    
    # Select random method for building command to reverse the above substitutions to execute the original command.
    # Avoid using the -f format operator (switch option 3) if curly braces are found in $ScriptString.
    If(($ScriptString.Contains('{')) -AND ($ScriptString.Contains('}')))
    {
        $RandomInput = Get-Random -Input (1..2)
    }
    Else
    {
        $RandomInput = Get-Random -Input (1..3)
    }

    # Randomize the case of selected variable syntaxes.
    $StringStr   = Out-RandomCase 'string'
    $CharStr     = Out-RandomCase 'char'
    $ReplaceStr  = Out-RandomCase 'replace'
    $CReplaceStr = Out-RandomCase 'creplace'

    Switch($RandomInput) {
        1 {
            # 1) .Replace

            $ScriptString = "'" + $ScriptString + "'"
            $ReversingCommand = ""

            ForEach($DelimiterArray in $DelimiterTableWithQuotes)
            {
                $Delimiter    = $DelimiterArray[0]
                $OriginalChar = $DelimiterArray[1]
                
                # Randomly decide if $OriginalChar will be displayed in ASCII representation or plaintext in $ReversingCommand.
                # This is to allow for simpler string manipulation on the command line.
                # Place priority on handling if $OriginalChar is a single- and double-quote.
                If($OriginalChar[1] -eq "'")
                {
                    $OriginalChar = "[$StringStr][$CharStr]39"
                    $Delimiter = "'" + $Delimiter.SubString(1,$Delimiter.Length-2) + "'"
                }
                ElseIf($OriginalChar[1] -eq '"')
                {
                    $OriginalChar = "[$StringStr][$CharStr]34"
                }
                Else
                {
                    If(Get-Random -Input (0..1))
                    {
                        $OriginalChar = "[$StringStr][$CharStr]" + [Int][Char]$OriginalChar[1]
                    }
                }
                
                # Randomly select if $Delimiter will be displayed in ASCII representation instead of plaintext in $ReversingCommand. 
                If(Get-Random -Input (0..1))
                {
                    # Convert $Delimiter string into a concatenation of [Char] representations of each characters.
                    # This is to avoid redundant replacement of single quotes if this function is run numerous times back-to-back.
                    $DelimiterCharSyntax = ""
                    For($i=1; $i -lt $Delimiter.Length-1; $i++)
                    {
                        $DelimiterCharSyntax += "[$CharStr]" + [Int][Char]$Delimiter[$i] + '+'
                    }
                    $Delimiter = '(' + $DelimiterCharSyntax.Trim('+') + ')'
                }
                
                # Add reversing commands to $ReversingCommand.
                $ReversingCommand = ".$ReplaceStr($Delimiter,$OriginalChar)" + $ReversingCommand
            }

            # Concatenate $ScriptString as a string and then encapsulate with parentheses.
            $ScriptString = Out-ConcatenatedString $ScriptString "'"
            $ScriptString = '(' + $ScriptString + ')'

            # Add reversing commands to $ScriptString.
            $ScriptString = $ScriptString + $ReversingCommand
        }
        2 {
            # 2) -Replace/-CReplace

            $ScriptString = "'" + $ScriptString + "'"
            $ReversingCommand = ""

            ForEach($DelimiterArray in $DelimiterTableWithQuotes)
            {
                $Delimiter    = $DelimiterArray[0]
                $OriginalChar = $DelimiterArray[1]
                
                # Randomly decide if $OriginalChar will be displayed in ASCII representation or plaintext in $ReversingCommand.
                # This is to allow for simpler string manipulation on the command line.
                # Place priority on handling if $OriginalChar is a single- or double-quote.
                If($OriginalChar[1] -eq '"')
                {
                    $OriginalChar = "[$CharStr]34"
                }
                ElseIf($OriginalChar[1] -eq "'")
                {
                    $OriginalChar = "[$CharStr]39"; $Delimiter = "'" + $Delimiter.SubString(1,$Delimiter.Length-2) + "'"
                }
                Else
                {
                    $OriginalChar = "[$CharStr]" + [Int][Char]$OriginalChar[1]
                }
                
                # Randomly select if $Delimiter will be displayed in ASCII representation instead of plaintext in $ReversingCommand. 
                If(Get-Random -Input (0..1))
                {
                    # Convert $Delimiter string into a concatenation of [Char] representations of each characters.
                    # This is to avoid redundant replacement of single quotes if this function is run numerous times back-to-back.
                    $DelimiterCharSyntax = ""
                    For($i=1; $i -lt $Delimiter.Length-1; $i++)
                    {
                        $DelimiterCharSyntax += "[$CharStr]" + [Int][Char]$Delimiter[$i] + '+'
                    }
                    $Delimiter = '(' + $DelimiterCharSyntax.Trim('+') + ')'
                }
                
                # Randomly choose between -Replace and the lesser-known case-sensitive -CReplace.
                $Replace = (Get-Random -Input @("-$ReplaceStr","-$CReplaceStr"))

                # Add reversing commands to $ReversingCommand. Whitespace before and after $Replace is optional.
                $ReversingCommand = ' '*(Get-Random -Minimum 0 -Maximum 3) + $Replace + ' '*(Get-Random -Minimum 0 -Maximum 3) + "$Delimiter,$OriginalChar" + $ReversingCommand                
            }

            # Concatenate $ScriptString as a string and then encapsulate with parentheses.
            $ScriptString = Out-ConcatenatedString $ScriptString "'"
            $ScriptString = '(' + $ScriptString + ')'

            # Add reversing commands to $ScriptString.
            $ScriptString = '(' + $ScriptString + $ReversingCommand + ')'
        }
        3 {
            # 3) -f format operator

            $ScriptString = "'" + $ScriptString + "'"
            $ReversingCommand = ""
            $Counter = 0

            # Iterate delimiters in reverse for simpler creation of the proper order for $ReversingCommand.
            For($i=$DelimiterTableWithQuotes.Count-1; $i -ge 0; $i--)
            {
                $DelimiterArray = $DelimiterTableWithQuotes[$i]
                
                $Delimiter    = $DelimiterArray[0]
                $OriginalChar = $DelimiterArray[1]
                
                $DelimiterNoQuotes = $Delimiter.SubString(1,$Delimiter.Length-2)
                
                # Randomly decide if $OriginalChar will be displayed in ASCII representation or plaintext in $ReversingCommand.
                # This is to allow for simpler string manipulation on the command line.
                # Place priority on handling if $OriginalChar is a single- or double-quote.
                If($OriginalChar[1] -eq '"')
                {
                    $OriginalChar = "[$CharStr]34"
                }
                ElseIf($OriginalChar[1] -eq "'")
                {
                    $OriginalChar = "[$CharStr]39"; $Delimiter = "'" + $Delimiter.SubString(1,$Delimiter.Length-2) + "'"
                }
                Else
                {
                    $OriginalChar = "[$CharStr]" + [Int][Char]$OriginalChar[1]
                }
                
                # Build out delimiter order to add as arguments to the final -f format operator.
                $ReversingCommand = $ReversingCommand + ",$OriginalChar"

                # Substitute each delimited character with placeholder for -f format operator.
                $ScriptString = $ScriptString.Replace($DelimiterNoQuotes,"{$Counter}")

                $Counter++
            }
            
            # Trim leading comma from $ReversingCommand.
            $ReversingCommand = $ReversingCommand.Trim(',')

            # Concatenate $ScriptString as a string and then encapsulate with parentheses.
            $ScriptString = Out-ConcatenatedString $ScriptString "'"
            $ScriptString = '(' + $ScriptString + ')'
            
            # Add reversing commands to $ScriptString. Whitespace before and after -f format operator is optional.
            $FormatOperator = (Get-Random -Input @('-f','-F'))

            $ScriptString = '(' + $ScriptString + ' '*(Get-Random -Minimum 0 -Maximum 3) + $FormatOperator + ' '*(Get-Random -Minimum 0 -Maximum 3) + $ReversingCommand + ')'
        }
        default {Write-Error "An invalid `$RandomInput value ($RandomInput) was passed to switch block."; Exit;}
    }
    
    # Encapsulate $ScriptString in necessary IEX/Invoke-Expression(s) if -PassThru switch was not specified.
    If(!$PSBoundParameters['PassThru'])
    {
        $ScriptString = Out-EncapsulatedInvokeExpression $ScriptString
    }

    Return $ScriptString
}

Function Out-StringDelimitedConcatenatedAndReordered
{
<#
.SYNOPSIS

Generates delimited, concatenated and reordered version of input PowerShell command.

Invoke-Obfuscation Function: Out-StringDelimitedConcatenatedAndReordered
Author: Daniel Bohannon (@danielhbohannon)
License: Apache License, Version 2.0
Required Dependencies: Out-StringDelimitedAndConcatenated (located in Out-ObfuscatedStringCommand.ps1)
Optional Dependencies: None
 
.DESCRIPTION

Out-StringDelimitedConcatenatedAndReordered delimits, concatenates and reorders the concatenated substrings of an input PowerShell command. The purpose is to highlight to the Blue Team that there are more novel ways to encode a PowerShell command other than the most common Base64 approach.

.PARAMETER ScriptString

Specifies the string containing your payload.

.PARAMETER PassThru

(Optional) Outputs the option to not encapsulate the result in an invocation command.

.EXAMPLE

C:\PS> Out-StringDelimitedConcatenatedAndReordered "Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green"

(("{16}{5}{6}{14}{3}{19}{15}{10}{18}{17}{0}{2}{7}{8}{12}{9}{11}{4}{13}{1}"-f't','en','ion R','9 -Fore','Gr','e-Host 0i9Hello W','or','ocks!0i9 -Fo','regroun','olo','ite-Hos','r ','dC','e','ld!0i','; Wr','Writ','sca','t 0i9Obfu','groundColor Green')).Replace('0i9',[String][Char]39) |IEX

.NOTES

This cmdlet is most easily used by passing a script block or file path to a PowerShell script into the Out-ObfuscatedStringCommand function with the corresponding obfuscation level since Out-Out-ObfuscatedStringCommand will handle calling this current function where necessary.
C:\PS> Out-ObfuscatedStringCommand {Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green} 2
This is a personal project developed by Daniel Bohannon while an employee at MANDIANT, A FireEye Company.

.LINK

http://www.danielbohannon.com
#>

    [CmdletBinding()] Param (
        [Parameter(Position = 0)]
        [ValidateNotNullOrEmpty()]
        [String]
        $ScriptString,

        [Switch]
        $PassThru
    )

    If(!$PSBoundParameters['PassThru'])
    {
        # Convert $ScriptString to delimited and concatenated string and encapsulate with invocation.
        $ScriptString = Out-StringDelimitedAndConcatenated $ScriptString
    }
    Else
    {
        # Convert $ScriptString to delimited and concatenated string and do no encapsulate with invocation.
        $ScriptString = Out-StringDelimitedAndConcatenated $ScriptString -PassThru
    }

    # Parse out concatenated strings to re-order them.
    $Tokens = [System.Management.Automation.PSParser]::Tokenize($ScriptString,[ref]$null)
    $GroupStartCount = 0
    $ConcatenatedStringsIndexStart = $NULL
    $ConcatenatedStringsIndexEnd   = $NULL
    $ConcatenatedStringsArray = @()
    For($i=0; $i -le $Tokens.Count-1; $i++) {
        $Token = $Tokens[$i]

        If(($Token.Type -eq 'GroupStart') -AND ($Token.Content -eq '('))
        {
            $GroupStartCount = 1
            $ConcatenatedStringsIndexStart = $Token.Start+1
        }
        ElseIf(($Token.Type -eq 'GroupEnd') -AND ($Token.Content -eq ')') -OR ($Token.Type -eq 'Operator') -AND ($Token.Content -ne '+'))
        {
            $GroupStartCount--
            $ConcatenatedStringsIndexEnd = $Token.Start
            # Stop parsing concatenated string.
            If(($GroupStartCount -eq 0) -AND ($ConcatenatedStringsArray.Count -gt 0))
            {
                Break
            }
        }
        ElseIf(($GroupStartCount -gt 0) -AND ($Token.Type -eq 'String'))
        {
            $ConcatenatedStringsArray += $Token.Content
        }
        ElseIf($Token.Type -ne 'Operator')
        {
            # If something other than a string or operator appears then we're not dealing with a pure string concatenation. Thus we reset the group start and the concatenated strings array.
            # This only became an issue once the invocation syntax went from IEX/Invoke-Expression to concatenations like .($ShellId[1]+$ShellId[13]+'x')
            $GroupStartCount = 0
            $ConcatenatedStringsArray = @()
        }
    }

    $ConcatenatedStrings = $ScriptString.SubString($ConcatenatedStringsIndexStart,$ConcatenatedStringsIndexEnd-$ConcatenatedStringsIndexStart)

    # Return $ScriptString as-is if there is only one substring as it would gain nothing to "reorder" a single substring.
    If($ConcatenatedStringsArray.Count -le 1)
    {
        Return $ScriptString
    }

    # Randomize the order of the concatenated strings.
    $RandomIndexes = (Get-Random -Input (0..$($ConcatenatedStringsArray.Count-1)) -Count $ConcatenatedStringsArray.Count)
    
    $Arguments1 = ''
    $Arguments2 = @('')*$ConcatenatedStringsArray.Count
    For($i=0; $i -lt $ConcatenatedStringsArray.Count; $i++)
    {
        $RandomIndex = $RandomIndexes[$i]
        $Arguments1 += '{' + $RandomIndex + '}'
        $Arguments2[$RandomIndex] = "'" + $ConcatenatedStringsArray[$i] + "'"
    }
    
    # Whitespace is not required before or after the -f operator.
    $ScriptStringReordered = '(' + '"' + $Arguments1 + '"' + ' '*(Get-Random @(0..1)) + '-f' + ' '*(Get-Random @(0..1)) + ($Arguments2 -Join ',') + ')'

    # Add re-ordered $ScriptString back into the original $ScriptString context.
    $ScriptString = $ScriptString.SubString(0,$ConcatenatedStringsIndexStart) + $ScriptStringReordered + $ScriptString.SubString($ConcatenatedStringsIndexEnd)

    Return $ScriptString
}

# =============================================================================
#           POWERSHELL SENTINEL - PUBLIC OBfuscation FUNCTIONS
# =============================================================================

function Invoke-SentinelConcat {
    [CmdletBinding()]
    Param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )
    
    # Call the extracted worker function directly.
    # The -PassThru switch is critical as it returns the raw obfuscated string
    # without any execution wrappers like IEX.
    $obfuscatedString = Out-StringDelimitedAndConcatenated -ScriptString $Command -PassThru
    
    # Return the clean, final string.
    return $obfuscatedString
}

function Invoke-SentinelFormat {
    [CmdletBinding()]
    Param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )
    
    # Call the extracted worker function for reordering/formatting.
    $obfuscatedString = Out-StringDelimitedConcatenatedAndReordered -ScriptString $Command -PassThru
    
    return $obfuscatedString
}

Function Out-ObfuscatedTypeToken
{
<#
.SYNOPSIS

Obfuscates type token by using direct type cast syntax and concatenating or reordering the Type token value.
This function only applies to Type tokens immediately followed by . or :: operators and then a Member token.
E.g. [Char][Int]'123' will not be obfuscated by this function, but [Console]::WriteLine will be obfuscated.

Invoke-Obfuscation Function: Out-ObfuscatedTypeToken
Author: Daniel Bohannon (@danielhbohannon)
License: Apache License, Version 2.0
Required Dependencies: Out-StringDelimitedAndConcatenated, Out-StringDelimitedConcatenatedAndReordered (both located in Out-ObfuscatedStringCommand.ps1)
Optional Dependencies: None
 
.DESCRIPTION

Out-ObfuscatedTypeToken obfuscates a given token and places it back into the provided PowerShell script to evade detection by simple IOCs and process execution monitoring relying solely on command-line arguments. For the most complete obfuscation all tokens in a given PowerShell script or script block (cast as a string object) should be obfuscated via the corresponding obfuscation functions and desired obfuscation levels in Out-ObfuscatedTokenCommand.ps1.

.PARAMETER ScriptString

Specifies the string containing your payload.

.PARAMETER Token

Specifies the token to obfuscate.

.PARAMETER ObfuscationLevel

Specifies whether to 1) Concatenate or 2) Reorder the Type token value.

.EXAMPLE

C:\PS> $ScriptString = "[console]::WriteLine('Hello World!'); [console]::WriteLine('Obfuscation Rocks!')"
C:\PS> $Tokens = [System.Management.Automation.PSParser]::Tokenize($ScriptString,[ref]$null) | Where-Object {$_.Type -eq 'Type'}
C:\PS> For($i=$Tokens.Count-1; $i -ge 0; $i--) {$Token = $Tokens[$i]; $ScriptString = Out-ObfuscatedTypeToken $ScriptString $Token 1}
C:\PS> $ScriptString

sET  EOU ( [TYPe]('CO'+'NS'+'oLe')) ;    (  CHILdiTEM  VariablE:EOU ).VALUE::WriteLine('Hello World!');   $eoU::WriteLine('Obfuscation Rocks!')

C:\PS> $ScriptString = "[console]::WriteLine('Hello World!'); [console]::WriteLine('Obfuscation Rocks!')"
C:\PS> $Tokens = [System.Management.Automation.PSParser]::Tokenize($ScriptString,[ref]$null) | Where-Object {$_.Type -eq 'Type'}
C:\PS> For($i=$Tokens.Count-1; $i -ge 0; $i--) {$Token = $Tokens[$i]; $ScriptString = Out-ObfuscatedTypeToken $ScriptString $Token 2}
C:\PS> $ScriptString

SET-vAriablE  BVgz6n ([tYpe]("{2}{1}{0}" -f'sOle','On','C')  )  ;    $BVGz6N::WriteLine('Hello World!');  ( cHilDItem  vAriAbLE:bVGZ6n ).VAlue::WriteLine('Obfuscation Rocks!')

.NOTES

This cmdlet is most easily used by passing a script block or file path to a PowerShell script into the Out-ObfuscatedTokenCommand function with the corresponding token type and obfuscation level since Out-ObfuscatedTokenCommand will handle token parsing, reverse iterating and passing tokens into this current function.
C:\PS> Out-ObfuscatedTokenCommand {[console]::WriteLine('Hello World!'); [console]::WriteLine('Obfuscation Rocks!')} 'Type' 1
C:\PS> Out-ObfuscatedTokenCommand {[console]::WriteLine('Hello World!'); [console]::WriteLine('Obfuscation Rocks!')} 'Type' 2
This is a personal project developed by Daniel Bohannon while an employee at MANDIANT, A FireEye Company.

.LINK

http://www.danielbohannon.com
#>

    [CmdletBinding()] Param (
        [Parameter(Position = 0, Mandatory = $True)]
        [ValidateNotNullOrEmpty()]
        [String]
        $ScriptString,
    
        [Parameter(Position = 1, Mandatory = $True)]
        [ValidateNotNullOrEmpty()]
        [System.Management.Automation.PSToken]
        $Token,

        [Parameter(Position = 2, Mandatory = $True)]
        [ValidateSet(1, 2)]
        [Int]
        $ObfuscationLevel
    )

    # If we are dealing with a Type that is found in $TypesThatCannotByDirectTypeCasted then return as is since it will error if we try to direct Type cast.
    ForEach($Type in $TypesThatCannotByDirectTypeCasted)
    {
        If($Token.Content.ToLower().Contains($Type))
        {
            Return $ScriptString
        }
    }

    # If we are dealing with a Type that is NOT immediately followed by a Member token (denoted by . or :: operators) then we won't obfuscated.
    # This is for Type tokens like: [Char][Int]'123' etc.
    If(($ScriptString.SubString($Token.Start+$Script:TypeTokenScriptStringGrowth+$Token.Length,1) -ne '.') -AND ($ScriptString.SubString($Token.Start+$Script:TypeTokenScriptStringGrowth+$Token.Length,2) -ne '::'))
    {
        Return $ScriptString
    }

    # This variable will be used to track the growth in length of $ScriptString since we'll be appending variable creation at the beginning of $ScriptString.
    # This will allow us to avoid tokenizing $ScriptString for every single Type token that is present.
    $PrevLength = $ScriptString.Length

    # See if we've already set another instance of this same Type token previously in this obfsucation iteration.
    $RandomVarName = $NULL
    $UsingPreviouslyDefinedVarName = $FALSE
    ForEach($DefinedTokenVariable in $Script:TypeTokenVariableArray)
    {
        If($Token.Content.ToLower() -eq $DefinedTokenVariable[0])
        {
            $RandomVarName = $DefinedTokenVariable[1]
            $UsingPreviouslyDefinedVarName = $TRUE
        }
    }

    # If we haven't already defined a random variable for this Token type then we will do that. Otherwise we will use the previously-defined variable.
    If(!($UsingPreviouslyDefinedVarName))
    {
        # User input $ObfuscationLevel (1-2) will choose between concatenating Type token value string (after trimming square brackets) or reordering it with the -F format operator.
        # I am leaving out Out-ObfuscatedStringCommand's option 3 since that may introduce another Type token unnecessarily ([Regex]).

        # Trim of encapsulating square brackets before obfuscating the string value of the Type token.
        $TokenContent = $Token.Content.Trim('[]')

        Switch($ObfuscationLevel)
        {
            1 {$ObfuscatedToken = Out-StringDelimitedAndConcatenated $TokenContent -PassThru}
            2 {$ObfuscatedToken = Out-StringDelimitedConcatenatedAndReordered $TokenContent -PassThru}
            default {Write-Error "An invalid `$ObfuscationLevel value ($ObfuscationLevel) was passed to switch block for Type Token Obfuscation."; Exit}
        }
        
        # Evenly trim leading/trailing parentheses.
        While($ObfuscatedToken.StartsWith('(') -AND $ObfuscatedToken.EndsWith(')'))
        {
            $ObfuscatedToken = ($ObfuscatedToken.SubString(1,$ObfuscatedToken.Length-2)).Trim()
        }

        # Add syntax for direct type casting.
        $ObfuscatedTokenTypeCast = '[type]' + '(' + $ObfuscatedToken + ')'

        # Characters we will use to generate random variable names.
        # For simplicity do NOT include single- or double-quotes in this array.
        $CharsToRandomVarName  = @(0..9)
        $CharsToRandomVarName += @('A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z')

        # Randomly choose variable name starting length.
        $RandomVarLength = (Get-Random -Input @(3..6))
   
        # Create random variable with characters from $CharsToRandomVarName.
        If($CharsToRandomVarName.Count -lt $RandomVarLength) {$RandomVarLength = $CharsToRandomVarName.Count}
        $RandomVarName = ((Get-Random -Input $CharsToRandomVarName -Count $RandomVarLength) -Join '').Replace(' ','')

        # Keep generating random variables until we find one that is not a substring of $ScriptString.
        While($ScriptString.ToLower().Contains($RandomVarName.ToLower()))
        {
            $RandomVarName = ((Get-Random -Input $CharsToRandomVarName -Count $RandomVarLength) -Join '').Replace(' ','')
            $RandomVarLength++
        }

        # Track this variable name and Type token so we can reuse this variable name for future uses of this same Type token in this obfuscation iteration.
        $Script:TypeTokenVariableArray += , @($Token.Content,$RandomVarName)
    }

    # Randomly decide if the variable name will be concatenated inline or not.
    # Handle both <varname> and <variable:varname> syntaxes depending on which option is chosen concerning GET variable syntax.
    $RandomVarNameMaybeConcatenated = $RandomVarName
    $RandomVarNameMaybeConcatenatedWithVariablePrepended = 'variable:' + $RandomVarName
    If((Get-Random -Input @(0..1)) -eq 0)
    {
        $RandomVarNameMaybeConcatenated = '(' + (Out-ConcatenatedString $RandomVarName (Get-Random -Input @('"',"'"))) + ')'
        $RandomVarNameMaybeConcatenatedWithVariablePrepended = '(' + (Out-ConcatenatedString "variable:$RandomVarName" (Get-Random -Input @('"',"'"))) + ')'
    }
    
    # Generate random variable SET syntax.
    $RandomVarSetSyntax  = @()
    $RandomVarSetSyntax += '$' + $RandomVarName + ' '*(Get-Random @(0..2)) + '=' + ' '*(Get-Random @(0..2)) + $ObfuscatedTokenTypeCast
    $RandomVarSetSyntax += (Get-Random -Input @('Set-Variable','SV','Set')) + ' '*(Get-Random @(1..2)) + $RandomVarNameMaybeConcatenated + ' '*(Get-Random @(1..2)) + '(' + ' '*(Get-Random @(0..2)) + $ObfuscatedTokenTypeCast + ' '*(Get-Random @(0..2)) + ')'
    $RandomVarSetSyntax += 'Set-Item' + ' '*(Get-Random @(1..2)) + $RandomVarNameMaybeConcatenatedWithVariablePrepended + ' '*(Get-Random @(1..2)) + '(' + ' '*(Get-Random @(0..2)) + $ObfuscatedTokenTypeCast + ' '*(Get-Random @(0..2)) + ')'

    # Randomly choose from above variable syntaxes.
    $RandomVarSet = (Get-Random -Input $RandomVarSetSyntax)

    # Randomize the case of selected variable syntaxes.
    $RandomVarSet = Out-RandomCase $RandomVarSet
  
    # Generate random variable GET syntax.
    $RandomVarGetSyntax  = @()
    $RandomVarGetSyntax += '$' + $RandomVarName
    $RandomVarGetSyntax += '(' + ' '*(Get-Random @(0..2)) + (Get-Random -Input @('Get-Variable','Variable')) + ' '*(Get-Random @(1..2)) + $RandomVarNameMaybeConcatenated + (Get-Random -Input ((' '*(Get-Random @(0..2)) + ').Value'),(' '*(Get-Random @(1..2)) + ('-ValueOnly'.SubString(0,(Get-Random -Minimum 3 -Maximum ('-ValueOnly'.Length+1)))) + ' '*(Get-Random @(0..2)) + ')')))
    $RandomVarGetSyntax += '(' + ' '*(Get-Random @(0..2)) + (Get-Random -Input @('DIR','Get-ChildItem','GCI','ChildItem','LS','Get-Item','GI','Item')) + ' '*(Get-Random @(1..2)) + $RandomVarNameMaybeConcatenatedWithVariablePrepended + ' '*(Get-Random @(0..2)) + ').Value'
    
    # Randomly choose from above variable syntaxes.
    $RandomVarGet = (Get-Random -Input $RandomVarGetSyntax)

    # Randomize the case of selected variable syntaxes.
    $RandomVarGet = Out-RandomCase $RandomVarGet

    # If we're using an existing variable already set in ScriptString for the current Type token then we don't need to prepend an additional SET variable syntax.
    $PortionToPrependToScriptString = ''
    If(!($UsingPreviouslyDefinedVarName))
    {
        $PortionToPrependToScriptString = ' '*(Get-Random @(0..2)) + $RandomVarSet  + ' '*(Get-Random @(0..2)) + ';' + ' '*(Get-Random @(0..2))
    }

    # Add the obfuscated token back to $ScriptString.
    $ScriptString = $PortionToPrependToScriptString + $ScriptString.SubString(0,$Token.Start+$Script:TypeTokenScriptStringGrowth) + ' '*(Get-Random @(1..2)) + $RandomVarGet + $ScriptString.SubString($Token.Start+$Token.Length+$Script:TypeTokenScriptStringGrowth)

    # Keep track how much $ScriptString grows for each Type token obfuscation iteration.
    $Script:TypeTokenScriptStringGrowth = $Script:TypeTokenScriptStringGrowth + $PortionToPrependToScriptString.Length

    Return $ScriptString
}

function Invoke-SentinelType {
    [CmdletBinding()]
    Param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    $Tokens = [System.Management.Automation.PSParser]::Tokenize($Command, [ref]$null)
    $ScriptString = $Command
    
    # Required for the Type worker function
    $Script:TypeTokenScriptStringGrowth = 0
    $Script:TypeTokenVariableArray = @()

    For ($i = $Tokens.Count - 1; $i -ge 0; $i--) {
        $Token = $Tokens[$i]
        if ($Token.Type -eq 'Type') {
            # Use obfuscation level 1 (Concatenate) for the Type name
            $ScriptString = Out-ObfuscatedTypeToken -ScriptString $ScriptString -Token $Token -ObfuscationLevel 1
        }
    }
    
    return $ScriptString
}

Function Out-ObfuscatedCommandTokenLevel2
{
<#
.SYNOPSIS

Obfuscates command token by converting it to a concatenated string and using splatting to invoke the command.

Invoke-Obfuscation Function: Out-ObfuscatedCommandTokenLevel2
Author: Daniel Bohannon (@danielhbohannon)
License: Apache License, Version 2.0
Required Dependencies: Out-StringDelimitedAndConcatenated, Out-StringDelimitedConcatenatedAndReordered (both located in Out-ObfuscatedStringCommand.ps1)
Optional Dependencies: None
 
.DESCRIPTION

Out-ObfuscatedCommandTokenLevel2 obfuscates a given command token and places it back into the provided PowerShell script to evade detection by simple IOCs and process execution monitoring relying solely on command-line arguments. For the most complete obfuscation all tokens in a given PowerShell script or script block (cast as a string object) should be obfuscated via the corresponding obfuscation functions and desired obfuscation levels in Out-ObfuscatedTokenCommand.ps1.

.PARAMETER ScriptString

Specifies the string containing your payload.

.PARAMETER Token

Specifies the token to obfuscate.

.PARAMETER ObfuscationLevel

Specifies whether to 1) Concatenate or 2) Reorder the splatted Command token value.

.EXAMPLE

C:\PS> $ScriptString = "Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green"
C:\PS> $Tokens = [System.Management.Automation.PSParser]::Tokenize($ScriptString,[ref]$null) | Where-Object {$_.Type -eq 'Command'}
C:\PS> For($i=$Tokens.Count-1; $i -ge 0; $i--) {$Token = $Tokens[$i]; $ScriptString = Out-ObfuscatedCommandTokenLevel2 $ScriptString $Token 1}
C:\PS> $ScriptString

&('Wr'+'itE-'+'HOSt') 'Hello World!' -ForegroundColor Green; .('WrITe-Ho'+'s'+'t') 'Obfuscation Rocks!' -ForegroundColor Green

C:\PS> $ScriptString = "Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green"
C:\PS> $Tokens = [System.Management.Automation.PSParser]::Tokenize($ScriptString,[ref]$null) | Where-Object {$_.Type -eq 'Command'}
C:\PS> For($i=$Tokens.Count-1; $i -ge 0; $i--) {$Token = $Tokens[$i]; $ScriptString = Out-ObfuscatedCommandTokenLevel2 $ScriptString $Token 1}
C:\PS> $ScriptString

&("{1}{0}{2}"-f'h','wRiTE-','ost') 'Hello World!' -ForegroundColor Green; .("{2}{1}{0}" -f'ost','-h','wrIte') 'Obfuscation Rocks!' -ForegroundColor Green

.NOTES

This cmdlet is most easily used by passing a script block or file path to a PowerShell script into the Out-ObfuscatedTokenCommand function with the corresponding token type and obfuscation level since Out-ObfuscatedTokenCommand will handle token parsing, reverse iterating and passing tokens into this current function.
C:\PS> Out-ObfuscatedTokenCommand {Write-Host 'Hello World!' -ForegroundColor Green; Write-Host 'Obfuscation Rocks!' -ForegroundColor Green} 'Command' 2
This is a personal project developed by Daniel Bohannon while an employee at MANDIANT, A FireEye Company.

.LINK

http://www.danielbohannon.com
#>

    [CmdletBinding()] Param (
        [Parameter(Position = 0, Mandatory = $True)]
        [ValidateNotNullOrEmpty()]
        [String]
        $ScriptString,
    
        [Parameter(Position = 1, Mandatory = $True)]
        [ValidateNotNullOrEmpty()]
        [System.Management.Automation.PSToken]
        $Token,

        [Parameter(Position = 2, Mandatory = $True)]
        [ValidateSet(1, 2)]
        [Int]
        $ObfuscationLevel
    )

    # Set $Token.Content in a separate variable so it can be modified since Content is a ReadOnly property of $Token.
    $TokenContent = $Token.Content

    # If ticks are already present in current Token then remove so they will not interfere with string concatenation.
    If($TokenContent.Contains('`')) {$TokenContent = $TokenContent.Replace('`','')}

    # Convert $Token to character array for easier manipulation.
    $TokenArray = [Char[]]$TokenContent
    
    # Randomly upper- and lower-case characters in current token.
    $ObfuscatedToken = Out-RandomCase $TokenArray

    # User input $ObfuscationLevel (1-2) will choose between concatenating Command token value string (after trimming square brackets) or reordering it with the -F format operator.
    # I am leaving out Out-ObfuscatedStringCommand's option 3 since that may introduce a Type token unnecessarily ([Regex]).
    Switch($ObfuscationLevel)
    {
        1 {$ObfuscatedToken = Out-StringDelimitedAndConcatenated $TokenContent -PassThru}
        2 {$ObfuscatedToken = Out-StringDelimitedConcatenatedAndReordered $TokenContent -PassThru}
        default {Write-Error "An invalid `$ObfuscationLevel value ($ObfuscationLevel) was passed to switch block for Command Token Obfuscation."; Exit}
    }
     
    # Evenly trim leading/trailing parentheses.
    While($ObfuscatedToken.StartsWith('(') -AND $ObfuscatedToken.EndsWith(')'))
    {
        $ObfuscatedToken = ($ObfuscatedToken.SubString(1,$ObfuscatedToken.Length-2)).Trim()
    }

    # Encapsulate $ObfuscatedToken with parentheses.
    $ObfuscatedToken = '(' + $ObfuscatedToken + ')'
    
    # Check if the command is already prepended with an invocation operator. If it is then do not add an invocation operator.
    # E.g. & powershell -Sta -Command $cmd
    # E.g. https://github.com/adaptivethreat/Empire/blob/master/data/module_source/situational_awareness/host/Invoke-WinEnum.ps1#L139
    $SubStringLength = 15
    If($Token.Start -lt $SubStringLength)
    {
        $SubStringLength = $Token.Start
    }

    # Extract substring leading up to the current token.
    $SubString = $ScriptString.SubString($Token.Start-$SubStringLength,$SubStringLength).Trim()

    # Set $InvokeOperatorAlreadyPresent boolean variable to TRUE if the substring ends with invocation operators . or &
    $InvokeOperatorAlreadyPresent = $FALSE
    If($SubString.EndsWith('.') -OR $SubString.EndsWith('&'))
    {
        $InvokeOperatorAlreadyPresent = $TRUE
    }

    If(!$InvokeOperatorAlreadyPresent)
    {
        # Randomly choose between the & and . Invoke Operators.
        # In certain large scripts where more than one parameter are being passed into a custom function 
        # (like Add-SignedIntAsUnsigned in Invoke-Mimikatz.ps1) then using . will cause errors but & will not.
        # For now we will default to only & if $ScriptString.Length -gt 10000
        If($ScriptString.Length -gt 10000) {$RandomInvokeOperator = '&'}
        Else {$RandomInvokeOperator = Get-Random -InputObject @('&','.')}
    
        # Add invoke operator (and potentially whitespace) to complete splatting command.
        $ObfuscatedToken = $RandomInvokeOperator + $ObfuscatedToken
    }

    # Add the obfuscated token back to $ScriptString.
    $ScriptString = $ScriptString.SubString(0,$Token.Start) + $ObfuscatedToken + $ScriptString.SubString($Token.Start+$Token.Length)
    
    Return $ScriptString
}

function Invoke-SentinelCommand {
    [CmdletBinding()]
    Param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )

    $Tokens = [System.Management.Automation.PSParser]::Tokenize($Command, [ref]$null)
    $ScriptString = $Command
    
    For ($i = $Tokens.Count - 1; $i -ge 0; $i--) {
        $Token = $Tokens[$i]
        if ($Token.Type -eq 'Command') {
            # Use obfuscation level 2 (Splatting + Concatenate)
            $ScriptString = Out-ObfuscatedCommandTokenLevel2 -ScriptString $ScriptString -Token $Token -ObfuscationLevel 1
            # The worker adds '& ' or '. ', so we break after the first command is found.
            break 
        }
    }
    
    return $ScriptString
}

function Invoke-SentinelBase64 {
    [CmdletBinding()]
    Param(
        [Parameter(Mandatory = $true)]
        [string]$Command
    )
    
    # Convert the command string to bytes using PowerShell's standard Unicode (UTF-16LE) encoding.
    $commandBytes = [System.Text.Encoding]::Unicode.GetBytes($Command)
    
    # Convert the bytes to a Base64 string.
    $encodedString = [System.Convert]::ToBase64String($commandBytes)
    
    # Return the final, complete command.
    return "powershell.exe -EncodedCommand $encodedString"
}

# Export ALL the public functions to make them available
Export-ModuleMember -Function Invoke-SentinelConcat, Invoke-SentinelFormat, Invoke-SentinelType, Invoke-SentinelCommand, Invoke-SentinelBase64