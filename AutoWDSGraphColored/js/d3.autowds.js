/* === HELPER === */

/* check if node is an ap */
function nodeIsAp(d) {
  return d.type == "AP";
}

/* check if link is fake link between radio and ap */
function linkIsFake(d) {
  return parseInt(d.sourcestrength) == 9000;
}
   
/* d3 size from css of container */
var width =  $("#d3container").width(),
    height = $("#d3container").height();
	
	
/* d3 layout */
var force = d3.layout.force()
	.charge(-200)
	.gravity(0.1)   /* default: 0.1 */
	.theta(0.8)     /* default: 0.8 */
	.friction(0.9)  /* default: 0.9 */
	.linkStrength(function(d){ 
	     if(linkIsFake(d)) 
		   /* link between ap and radio */
		   return 4;    
	     else 
		   /* link between radio and radio */
	       return 0.5;  
	  })
    .size([width, height])
	.on("tick", function() { force.tick(); });

/* drag */
var drag = force.drag()
    .on("dragstart", dragstart);
	
/* d3 svg */
var svg = d3.select("body #d3container").append("svg")
    .attr("width", width)
    .attr("height", height);

/* constructs objects */
d3.json(jsonFile, function(error, graph) {
   force
      .nodes(graph.nodes)
      .links(graph.links)
      .start();

  /* === HELPER === */
   
  /* returns channel of source radio of a link */
  function getSourceChannel(d) {
    return parseInt(graph.nodes[parseInt(d.source.index)].channel);
  }

  /* returns channel of target radio of a link */
  function getTargetChannel(d) {
    return parseInt(graph.nodes[parseInt(d.target.index)].channel);
  }

  /* === LINKS === */
   
  /* constructs links */
  var link = svg.selectAll(".link")
      .data(graph.links)
    .enter().append("line")
      .attr("class", "link")
	  	.style("stroke", function(d) { 
		   if(linkIsFake(d)) 
		     /* link between ap and radio */
		     return "#C1C1C1"; 
		   else 
		   {
		     /* link between radio and radio */
			 channel = parseInt(graph.nodes[parseInt(d.source.index)].channel);
			 targetchannel = parseInt(graph.nodes[parseInt(d.target.index)].channel);
			 
			 /* source channel != target channel */
			 if(channel != targetchannel) return "#CC0000";
			 
			 /* INACTIVE LINK */
			 if(d.state != "Active") return "#FF0000";
			 
			 /* 2.4GHz */
			 if(channel == 1)  return "#336699";
			 if(channel == 2)  return "#0000CC";
			 if(channel == 3)  return "#333399";
			 if(channel == 4)  return "#0099CC";
			 if(channel == 5)  return "#0066FF";
			 if(channel == 6)  return "#6600FF";
			 if(channel == 7)  return "#33CCFF";
			 if(channel == 8)  return "#009999";
			 if(channel == 9)  return "#006666";
			 if(channel == 10) return "#339966";
			 if(channel == 11) return "#006600";
			 if(channel == 12) return "#6600FF";
			 if(channel == 13) return "#9900CC";
			 
			 /* 5GHz UNII-1 Band*/
			 if(channel == 36) return "#CCA37A";   
			 if(channel == 40) return "#FF6600";   
			 if(channel == 44) return "#754719";   
			 if(channel == 48) return "#996633";   
			 
			 /* 5GHz UNII-2 Band*/
			 if(channel == 52) return "#993366";   
			 if(channel == 56) return "#660033";   
			 if(channel == 60) return "#990033";   
			 if(channel == 64) return "#DA4791";   
			 
			 /* 5GHz UNII-2 Band Extended */
			 if(channel == 100) return "#666633";   
			 if(channel == 104) return "#666633";   
			 if(channel == 108) return "#666633";   
			 if(channel == 112) return "#666633";   
			 if(channel == 116) return "#666633";   
			 if(channel == 120) return "#666633";   
			 if(channel == 124) return "#666633";   
			 if(channel == 128) return "#666633";   
			 if(channel == 132) return "#666633";   
			 if(channel == 136) return "#666633";   
			 
			 /* 5GHz UNII-3 Band */
			 if(channel == 149) return "#CCCC00";   
			 if(channel == 153) return "#CCCC00";   
			 if(channel == 157) return "#CCCC00";   
			 if(channel == 161) return "#CCCC00";   
			 
			 /* default */
			 return "#000000";

            }
	     })
	  	.style("stroke-width", function(d) { 
		   if(linkIsFake(d))
             /* link between ap and radio */
			 return 9;    
		   else 
		   {
  		     channel = parseInt(graph.nodes[parseInt(d.source.index)].channel);
			 targetchannel = parseInt(graph.nodes[parseInt(d.target.index)].channel);
			 
			 /* source channel != target channel */
             if(channel != targetchannel) return 7;

  			 /* INACTIVE LINK */
			 if(d.state != "Active") return 7;

		     /* link between radio and radio */
		     return (parseInt(d.sourcestrength)+parseInt(d.targetstrength))/18;
		   }
		   })
  		.style("stroke-dasharray", function(d) { 
		     if(linkIsFake(d)) 
			   /* link between ap and radio */
			   return "0,0"; 
			 else 
			 {
   			   channel = getSourceChannel(d);
			   targetchannel = getTargetChannel(d);
			 
			   /* source channel != target channel */
			   if(channel != targetchannel) return "6,8";

			   /* INACTIVE LINK */
			   if(d.state != "Active") return "6,8";
			   
			   /* link between radio and radio */
			   return "6,1"; 
			 }
			 });

  /* === NODES === */
  
  /* constructs nodes */
  var node = svg.selectAll(".node")
     .data(graph.nodes)
     .enter().append("circle")
      .attr("class", "node")
      .attr("r", function(d) {
	    if(nodeIsAp(d))
		  return 7; 
		else 
		  return 5; 
	   })
      .style("fill", function(d) { if(nodeIsAp(d)) return "#47A3FF"; else { if(d.label == "WLAN-1") return "#222222"; else return "#656565"; }; })
      //.call(force.drag); /* normal drag */
      .on("dblclick", dblclicknode)
	  .call(drag);
	  

  
  
  /* does positioning */
  force.on("tick", function() {
    link.attr("x1", function(d) { return d.source.x; })
        .attr("y1", function(d) { return d.source.y; })
        .attr("x2", function(d) { return d.target.x; })
        .attr("y2", function(d) { return d.target.y; });

    node.attr("cx", function(d) { return d.x; })
        .attr("cy", function(d) { return d.y; });
		
  });
  
  /* === TOOLTIP === */

  /* this tipsy shows us the tooltip info for interfaces and aps */
   $('svg circle.node').tipsy({ 
		gravity: 'w', 
		html: true,
		fade: false,
        title: function() {
          var d = this.__data__;
          return d.type+': '+d.label+'<br/>MAC: '+d.mac+(d.channel != "" ? "<br/>"+(d.channel>=36 ? "5GHz":"2.4GHz")+", Channel "+d.channel+"" : ""); 
        }
      });

  /* this tipsy shows us the tooltip info for links */
   $('svg .link').tipsy({ 
        trigger: 'hover',
		gravity: 's', 
		html: true,
		fade: false,
        title: function() {
          var d = this.__data__;
		  if(linkIsFake(d))
		  {
		    /* link between radio and ap */
			return "links ap and radio (no info)";
		  }
		  else
		  {
		    /* link between radio and radio */
			channel = getSourceChannel(d);
		    return 'Source MAC: '+d.sourcemac+'<br/>Target MAC: '+d.targetmac+'<br/>Source Strength: '+d.sourcestrength+'<br/>Target Strength: '+d.targetstrength+(channel > 0 ? "<br/>"+(channel>=36 ? "5GHz":"2.4GHz")+", Channel "+channel+"" : "")+'<br/>State: '+d.state; 
		  }
        }
      });
	  
});

  /* DRAG */
  function dblclicknode(d) {
    if(nodeIsAp(d))
      d3.select(this).classed("fixed", d.fixed = false);
  }

  function dragstart(d) {
    if(nodeIsAp(d))
      d3.select(this).classed("fixed", d.fixed = true);
  }
