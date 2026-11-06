// Read-only bridge to the installed NetBalancer 12.6.1 local service.
// Writes still go exclusively through NBCMD. No arbitrary method selection.
using System;using System.IO;using System.Linq;using System.Reflection;using System.Collections;using System.Collections.Generic;using System.Runtime.Remoting.Channels;using System.Runtime.Remoting.Channels.Ipc;using System.Security.Principal;using System.Security.Cryptography;using System.Text;using System.Web.Script.Serialization;
class NetBalancerReadback {
 const string ExpectedCore="60e07aea24c7b400d182917b0dcd04cbd481f07d0ff3fe4cbfd80604caba2d65";
 static string Vendor="C:\\Program Files\\NetBalancer";
 static int Main(string[] args){Console.OutputEncoding=new UTF8Encoding(false);try{
  if(args.Length>1)throw new Exception("Only an optional application path is accepted");
  string file=Path.Combine(Vendor,"SeriousBit.NetBalancer.Core.dll"),hash;
  using(var stream=File.OpenRead(file))hash=String.Join("",SHA256.Create().ComputeHash(stream).Select(b=>b.ToString("x2")));
  if(hash!=ExpectedCore)throw new Exception("NetBalancer component changed; reader requires revalidation");
  AppDomain.CurrentDomain.AssemblyResolve+=(s,e)=>{var loaded=AppDomain.CurrentDomain.GetAssemblies().FirstOrDefault(a=>a.FullName==e.Name);if(loaded!=null)return loaded;string dependency=Path.Combine(Vendor,new AssemblyName(e.Name).Name+".dll");return File.Exists(dependency)?Assembly.LoadFrom(dependency):null;};
  var assembly=Assembly.LoadFrom(file);var method=(MethodInfo)assembly.ManifestModule.ResolveMethod(100663834);
  if(!method.IsPublic||method.IsStatic||method.GetParameters().Length!=0||method.ReturnType.FullName!="SeriousBit.NetBalancer.Core.Priorities.AppPriority[]"||method.DeclaringType.BaseType!=typeof(MarshalByRefObject)||!method.DeclaringType.GetProperties().Any(p=>p.GetGetMethod()==method))throw new Exception("Unexpected read-only getter signature");
  var props=new Hashtable();props["secure"]=true;props["tokenImpersonationLevel"]=TokenImpersonationLevel.Impersonation;
  ChannelServices.RegisterChannel(new IpcClientChannel(props,null),true);
  object service=Activator.GetObject(method.DeclaringType,"ipc://NetBalancer/IPCLink");
  var data=(IEnumerable)method.Invoke(service,new object[0]);var rows=new List<object>();
  foreach(object row in data){string path=Convert.ToString(row.GetType().GetProperty("Key").GetValue(row,null));if(args.Length==1&&!String.Equals(Path.GetFullPath(path),Path.GetFullPath(args[0]),StringComparison.OrdinalIgnoreCase))continue;
   var priority=row.GetType().GetProperty("Priority").GetValue(row,null);var fields=new Dictionary<string,string>();fields["Key"]=path;
   foreach(var property in priority.GetType().GetProperties())fields[property.Name]=Convert.ToString(property.GetValue(priority,null),System.Globalization.CultureInfo.InvariantCulture);
   rows.Add(fields);
  }
  Console.WriteLine(new JavaScriptSerializer().Serialize(new {status="valid",source="NetBalancer local authenticated IPC",sampled_at=(DateTime.UtcNow-new DateTime(1970,1,1)).TotalSeconds,core_sha256=hash,records=rows}));return 0;
 }catch(Exception ex){while(ex.InnerException!=null)ex=ex.InnerException;Console.WriteLine(new JavaScriptSerializer().Serialize(new{status="unavailable",error=ex.GetType().Name+": "+ex.Message}));return 1;}}
}
