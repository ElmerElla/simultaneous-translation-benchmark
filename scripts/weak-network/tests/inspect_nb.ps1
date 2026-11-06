$ErrorActionPreference='Stop'
$vendorRoot='C:\Program Files\NetBalancer'
[AppDomain]::CurrentDomain.add_ReflectionOnlyAssemblyResolve({param($sender,$request)
    $assemblyName=[Reflection.AssemblyName]::new($request.Name)
    $candidate=Join-Path 'C:\Program Files\NetBalancer' ($assemblyName.Name+'.dll')
    if(Test-Path -LiteralPath $candidate){return [Reflection.Assembly]::ReflectionOnlyLoadFrom($candidate)}
    return [Reflection.Assembly]::ReflectionOnlyLoad($request.Name)
})
$assembly=[Reflection.Assembly]::ReflectionOnlyLoadFrom((Join-Path $vendorRoot 'SeriousBit.NetBalancer.Core.dll'))
try{$types=$assembly.GetTypes()}catch [Reflection.ReflectionTypeLoadException]{$types=$_.Exception.Types | Where-Object {$_}}
$wanted=$args[0]
if($wanted -eq '--all'){$types | Where-Object {$_.IsPublic} | ForEach-Object {"$($_.MetadataToken) $($_.FullName)"};exit}
if($wanted -eq '--returns'){
    foreach($t in $types){foreach($m in $t.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Static,Instance,DeclaredOnly')){
        if($m.ReturnType.FullName -match 'AllSettings|AppPriority\[\]' -or $m.GetParameters().ParameterType.FullName -contains 'SeriousBit.NetBalancer.Core.AllSettings'){
            "TYPE $($t.MetadataToken) $($t.FullName) METHOD $($m.MetadataToken) STATIC $($m.IsStatic) $($m.ToString())"
        }
    }};exit
}
if(-not $wanted){$types | Where-Object {$_.IsPublic -and $_.FullName -match 'Priorit|Service|Client|Remote|Config|AppData|Process|Controller|Connection|Setting'} | ForEach-Object {$_.FullName};exit}
$type=$types | Where-Object {$_.FullName -eq $wanted -or ($wanted -match '^\d+$' -and $_.MetadataToken.ToString() -eq $wanted)}
if($args[1] -eq '--brief'){
    'BASE '+$type.BaseType.FullName
    $type.GetInterfaces() | ForEach-Object {'INTERFACE '+$_.FullName}
    $type.GetConstructors([Reflection.BindingFlags]'Public,NonPublic,Static,Instance') | ForEach-Object {"CTOR $($_.MetadataToken) $((@($_.GetParameters() | ForEach-Object {$_.ParameterType.FullName})) -join ',')"}
    $type.GetMethods([Reflection.BindingFlags]'Public,Static,Instance,DeclaredOnly') | ForEach-Object {"METHOD $($_.MetadataToken) STATIC $($_.IsStatic) RETURN $($_.ReturnType.FullName) ARGS $((@($_.GetParameters() | ForEach-Object {$_.ParameterType.FullName})) -join ',')"}
    $type.GetProperties([Reflection.BindingFlags]'Public,Static,Instance,DeclaredOnly') | ForEach-Object {'PROPERTY '+$_.ToString()}
    $type.GetMethods([Reflection.BindingFlags]'Public,Static,Instance,DeclaredOnly') | Where-Object {$_.ReturnType.FullName -match 'AppPriority|NetworkAdapter' -or $_.MetadataToken -eq 100663831} | ForEach-Object {"PARAMETERS $($_.MetadataToken) $((@($_.GetParameters() | ForEach-Object {$_.Name+':'+$_.ParameterType.FullName})) -join ',')"}
    exit
}
$type.GetMethods([Reflection.BindingFlags]'Public,Static,Instance,DeclaredOnly') | ForEach-Object {$_.ToString()}
$type.GetFields([Reflection.BindingFlags]'Public,Static,Instance,DeclaredOnly') | ForEach-Object {'FIELD '+$_.ToString()}
$type.GetProperties([Reflection.BindingFlags]'Public,Static,Instance,DeclaredOnly') | ForEach-Object {'PROPERTY '+$_.ToString()}
