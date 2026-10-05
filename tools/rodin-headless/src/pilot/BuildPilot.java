package pilot;
import java.nio.file.*;
import java.util.*;
import org.eclipse.equinox.app.*;
import org.eclipse.core.resources.*;
import org.eclipse.core.runtime.*;
import org.eventb.core.*;
import org.eventb.core.seqprover.IConfidence;
import org.rodinp.core.*;
public class BuildPilot implements IApplication {
 public Object start(IApplicationContext context)throws Exception {
  String[] args=(String[])context.getArguments().get(IApplicationContext.APPLICATION_ARGS);
  IWorkspace ws=ResourcesPlugin.getWorkspace();IProject project=ws.getRoot().getProject("AutomotivePilot");
  IProjectDescription d=ws.newProjectDescription("AutomotivePilot");
  d.setNatureIds(new String[]{"org.rodinp.core.rodinnature"});
  ICommand cmd=d.newCommand();cmd.setBuilderName("org.rodinp.core.rodinbuilder");d.setBuildSpec(new ICommand[]{cmd});
  project.create(d,null);project.open(null);
  for(java.nio.file.Path p:Files.list(java.nio.file.Path.of(args[0])).toList())if(!p.getFileName().toString().startsWith("."))
   try(var s=Files.newInputStream(p)){project.getFile(p.getFileName().toString()).create(s,true,null);}
  EventBPlugin.getAutoPostTacticManager().getAutoTacticPreference().setEnabled(false);
  EventBPlugin.getAutoPostTacticManager().getPostTacticPreference().setEnabled(false);
  ws.build(IncrementalProjectBuilder.FULL_BUILD,new NullProgressMonitor());
  for(IMarker m:project.findMarkers(null,true,IResource.DEPTH_INFINITE))
   System.out.println("MARKER "+m.getResource().getName()+": "+m.getAttribute(IMarker.MESSAGE,""));
  EventBPlugin.getAutoPostTacticManager().getAutoTacticPreference().setEnabled(true);
  IRodinProject rp=RodinCore.valueOf(project);
  List<IEventBRoot> roots=new ArrayList<>();
  roots.addAll(Arrays.asList(rp.getRootElementsOfType(IContextRoot.ELEMENT_TYPE)));
  roots.addAll(Arrays.asList(rp.getRootElementsOfType(IMachineRoot.ELEMENT_TYPE)));
  for(IEventBRoot root:roots){
   IPSRoot ps=root.getPSRoot();if(!ps.exists()){System.out.println("NO PO: "+root.getComponentName());continue;}
   var support=EventBPlugin.getUserSupportManager().newUserSupport();
   support.setInput(ps);support.loadProofStates();
   var defaultTac=EventBPlugin.getAutoPostTacticManager().getSelectedAutoTactics(root);
   for(IPSStatus status:ps.getStatuses()) {
    if(status.getConfidence()>IConfidence.PENDING)continue;
    support.setCurrentPO(status,new NullProgressMonitor());
    var state=support.getCurrentPO();state.loadProofTree(new NullProgressMonitor());
    var hyps=new ArrayList<org.eventb.core.ast.Predicate>();
    for(var h:state.getCurrentNode().getSequent().hypIterable())hyps.add(h);
    var show=org.eventb.core.seqprover.eventbExtensions.Tactics.mngHyp(org.eventb.core.seqprover.ProverFactory.makeShowHypAction(hyps));
    var select=org.eventb.core.seqprover.eventbExtensions.Tactics.mngHyp(org.eventb.core.seqprover.ProverFactory.makeSelectHypAction(hyps));
    var tac=org.eventb.core.seqprover.tactics.BasicTactics.composeOnAllPending(show,select,org.eventb.core.seqprover.eventbExtensions.Tactics.autoRewrite(),defaultTac);
    support.applyTactic(tac,false,new NullProgressMonitor());
    if(!state.isClosed())for(var node:state.getProofTree().getRoot().getOpenDescendants())
     System.out.println("GOAL "+status.getElementName()+" "+node.getSequent().goal());
    if(state.isClosed()) {
     support.doSave(new org.eventb.core.pm.IProofState[]{state},new NullProgressMonitor());
     System.out.println("CLOSED "+root.getComponentName()+" "+status.getElementName());
    } else System.out.println("PENDING "+root.getComponentName()+" "+status.getElementName());
   }
   support.dispose();
   int discharged=0;
   for(IPSStatus s:ps.getStatuses())if(s.getConfidence()>IConfidence.PENDING)discharged++;else System.out.println("UNPROVED "+root.getComponentName()+" "+s.getElementName());
   System.out.println("RESULT "+root.getComponentName()+" "+discharged+"/"+ps.getStatuses().length);
  }
  ws.save(true,new NullProgressMonitor());return IApplication.EXIT_OK;
 }
 public void stop(){}
}
