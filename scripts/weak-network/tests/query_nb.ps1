$ErrorActionPreference='Stop'
$vendorRoot='C:\Program Files\NetBalancer'
[AppDomain]::CurrentDomain.add_AssemblyResolve({param($sender,$request)
    $candidate=Join-Path 'C:\Program Files\NetBalancer' (([Reflection.AssemblyName]::new($request.Name)).Name+'.dll')
    if(Test-Path -LiteralPath $candidate){return [Reflection.Assembly]::LoadFrom($candidate)}
    return $null
})
try {
    $assembly=[Reflection.Assembly]::LoadFrom((Join-Path $vendorRoot 'SeriousBit.NetBalancer.Core.dll'))
    $method=$assembly.ManifestModule.ResolveMethod(100663905)
    if($args[0]){$method=$assembly.ManifestModule.ResolveMethod([int]$args[0])}
    $values=$method.Invoke($null,@())
    $rows=@($values | ForEach-Object {
        $valuesByName=[ordered]@{Key=$_.Key}
        foreach($property in $_.Priority.GetType().GetProperties()){$valuesByName[$property.Name]=$property.GetValue($_.Priority,$null).ToString()}
        $valuesByName
    })
    ConvertTo-Json -InputObject $rows -Depth 5
} catch {
    $errorValue=$_.Exception
    while($errorValue.InnerException){$errorValue=$errorValue.InnerException}
    Write-Output ($errorValue.GetType().Name+': '+$errorValue.Message)
    exit 1
}
