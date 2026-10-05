import java.nio.file.*;
import java.io.*;
import java.util.*;
import javax.xml.parsers.*;
import org.w3c.dom.Element;
import de.be4.classicalb.core.parser.BParser;
import de.be4.classicalb.core.parser.node.*;
import de.be4.classicalb.core.parser.analysis.prolog.*;
import de.prob.prolog.output.*;

// Restricted exporter for this pilot's native Rodin components.
// Structure follows ProB Java API EventBModelTranslator; no PO metadata is exported.
class ExportForProB {
  static final String P="org.eventb.core.";
  static String attr(Element e,String a){return e.getAttribute(P+a);}
  static List<Element> elements(Element root,String tag){
    List<Element> list=new ArrayList<>();
    for(var n=root.getFirstChild();n!=null;n=n.getNextSibling())
      if(n instanceof Element e&&e.getTagName().equals(P+tag)) list.add(e);
    return list;
  }
  static Element load(Path p)throws Exception{return DocumentBuilderFactory.newInstance().newDocumentBuilder().parse(p.toFile()).getDocumentElement();}
  static String ascii(String s){
    return s.replace("ℕ1","NAT1").replace("ℕ","NATURAL").replace("∈",":").replace("∉","/:")
      .replace("∧"," & ").replace("∨"," or ").replace("⇒"," => ").replace("≠","/=")
      .replace("↦","|->").replace("→","-->").replace("×","*").replace("‥","..")
      .replace("−","-").replace("∗","*").replace("≔",":=");
  }
  static PPredicate pred(String s)throws Exception{
    if(s.startsWith("partition(")) {
      String[] args=s.substring(10,s.length()-1).split(",");
      List<PExpression> parts=new ArrayList<>();
      for(int i=1;i<args.length;i++)parts.add(expr(args[i].trim()));
      return new APartitionPredicate(expr(args[0].trim()),parts);
    }
    return ((APredicateParseUnit)new BParser().parsePredicate(ascii(s)).getPParseUnit()).getPredicate();
  }
  static PExpression expr(String s)throws Exception{return ((AExpressionParseUnit)new BParser().parseExpression(ascii(s)).getPParseUnit()).getExpression();}
  static PSubstitution sub(String s)throws Exception{return ((ASubstitutionParseUnit)new BParser().parseSubstitution(ascii(s)).getPParseUnit()).getSubstitution();}
  static List<TIdentifierLiteral> targets(Element root,String tag,String a){
    List<TIdentifierLiteral> list=new ArrayList<>();
    for(Element e:elements(root,tag))list.add(new TIdentifierLiteral(attr(e,a)));
    return list;
  }
  static List<PExpression> identifiers(Element root,String tag)throws Exception{
    List<PExpression> list=new ArrayList<>();
    for(Element e:elements(root,tag))list.add(expr(attr(e,"identifier")));
    return list;
  }
  static List<PPredicate> predicates(Element root,String tag)throws Exception{
    List<PPredicate> list=new ArrayList<>();
    for(Element e:elements(root,tag))list.add(pred(attr(e,"predicate")));
    return list;
  }
  static Node context(Path file)throws Exception{
    Element xml=load(file);var ast=new AEventBContextParseUnit();
    ast.setName(new TIdentifierLiteral(file.getFileName().toString().replace(".buc","")));
    List<PContextClause> clauses=new ArrayList<>();
    clauses.add(new AExtendsContextClause(targets(xml,"extendsContext","target")));
    clauses.add(new AConstantsContextClause(identifiers(xml,"constant")));
    clauses.add(new AAbstractConstantsContextClause(new ArrayList<>()));
    clauses.add(new AAxiomsContextClause(predicates(xml,"axiom")));
    clauses.add(new ATheoremsContextClause(new ArrayList<>()));
    List<PSet> sets=new ArrayList<>();
    for(Element e:elements(xml,"carrierSet"))sets.add(new ADeferredSetSet(List.of(new TIdentifierLiteral(attr(e,"identifier")))));
    clauses.add(new ASetsContextClause(sets));ast.setContextClauses(clauses);return ast;
  }
  static Node machine(Path file)throws Exception{
    Element xml=load(file);var ast=new AEventBModelParseUnit();
    ast.setName(new TIdentifierLiteral(file.getFileName().toString().replace(".bum","")));
    List<PModelClause> clauses=new ArrayList<>();
    clauses.add(new ASeesModelClause(targets(xml,"seesContext","target")));
    for(Element e:elements(xml,"refinesMachine"))clauses.add(new ARefinesModelClause(new TIdentifierLiteral(attr(e,"target"))));
    clauses.add(new AVariablesModelClause(identifiers(xml,"variable")));
    clauses.add(new AInvariantModelClause(predicates(xml,"invariant")));
    clauses.add(new ATheoremsModelClause(new ArrayList<>()));
    for(Element e:elements(xml,"variant"))clauses.add(new AVariantModelClause(expr(attr(e,"expression"))));
    List<PEvent> events=new ArrayList<>();
    for(Element e:elements(xml,"event")){
      AEvent event=new AEvent();event.setEventName(new TIdentifierLiteral(attr(e,"label")));
      event.setStatus(attr(e,"convergence").equals("1")?new AConvergentEventstatus():new AOrdinaryEventstatus());
      event.setRefines(targets(e,"refinesEvent","target"));event.setVariables(identifiers(e,"parameter"));
      if(attr(e,"label").equals("INITIALISATION")&&!elements(xml,"refinesMachine").isEmpty())
        event.setRefines(List.of(new TIdentifierLiteral("INITIALISATION")));
      event.setGuards(predicates(e,"guard"));event.setTheorems(new ArrayList<>());
      List<PWitness> witnesses=new ArrayList<>();
      for(Element w:elements(e,"witness"))witnesses.add(new AWitness(new TIdentifierLiteral(attr(w,"label")),pred(attr(w,"predicate"))));
      event.setWitness(witnesses);
      List<PSubstitution> actions=new ArrayList<>();
      for(Element a:elements(e,"action"))actions.add(sub(attr(a,"assignment")));
      event.setAssignments(actions);events.add(event);
    }
    clauses.add(new AEventsModelClause(events));ast.setModelClauses(clauses);return ast;
  }
  public static void main(String[] args)throws Exception{
    Path directory=Path.of(args[0]);String main=args[1];
    try(var stream=new FileOutputStream(args[2])){
      var pto=new PrologTermOutput(stream,false);
      PositionPrinter pp=new PositionPrinter(){
        public void setPrologTermOutput(IPrologTermOutput output){}
        public void printPosition(Node n){pto.printAtom("none");}
        public void printPositionRange(Node a,Node b){pto.printAtom("none");}
      };
      ASTProlog printer=new ASTProlog(pto,pp);
      pto.openTerm("package");pto.openTerm("load_event_b_project");
      pto.openList();machine(directory.resolve(main+".bum")).apply(printer);
      if(main.equals("M1_SampledCycle"))machine(directory.resolve("M0_AtomicCycle.bum")).apply(printer);
      pto.closeList();pto.openList();context(directory.resolve("C_AutomotivePilot.buc")).apply(printer);pto.closeList();
      pto.openList();pto.openTerm("exporter_version");pto.printNumber(3);pto.closeTerm();pto.closeList();
      pto.printVariable("_Error");pto.closeTerm();pto.closeTerm();pto.fullstop();pto.flush();
    }
    System.out.println("Exported "+args[2]);
  }
}
