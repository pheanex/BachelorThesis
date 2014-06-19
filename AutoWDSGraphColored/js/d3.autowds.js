/*
 *  @file    d3.autowds.js
 *  @author  Christoph Wollgarten (christoph.wollgarten@lancom.de)
 *  @date    2014/06/06
 *  @version 0.2
 *
 */

/* === HELPER === */

var seenVisible=true;

/* check if node is an ap */
function nodeIsAp(d) {
  return d.type == "AP";
}

/* check if link is fake link between radio and ap */
function linkIsFake(d) {
  return d.connectiontype == "fake";
}

/* check if link is seen link between radio and radio */
function linkIsSeen(d) {
  return d.connectiontype == "seen";
}

/* filter low strength seen links */
function linkFilter(d) {
  if(linkIsSeen(d))
  {
    return seenVisible && !(d.sourcestrength=="" || d.targetstrength=="" || parseInt(d.sourcestrength) < 20 || parseInt(d.targetstrength) < 20) 
  }
  return true;
}

/* d3 size from css of container */
var width =  $("#d3container").width(),
    height = $("#d3container").height();

/* d3 layout */
var force = d3.layout.force()
	.charge(-300)
	.gravity(0.1)    /* default: 0.1 */
	.theta(0.8)      /* default: 0.8 */
	.friction(0.9)   /* default: 0.9 */
	.linkStrength(function(d){ 
	     if(linkIsFake(d))
		   return 10;               /* fake between ap and radio */
		 else if(linkIsSeen(d))
		 {
		   /* seen between radio and radio */
		   if(d.sourcestrength=="") d.sourcestrength = 0;
		   if(d.targetstrength=="") d.targetstrength = 0;
		   return 0.005*(((parseInt(d.sourcestrength)+parseInt(d.targetstrength))/200)^2); /* seen link between radio and radio */
		 }
	     else 
	       return 0.8;             /* p2p link between radio and radio */
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

/* z-order of elements */
var layerLinksSeen = svg.append('g');
var layerLinksReal = svg.append('g');
var layerLinksFake = svg.append('g');
var layerNodesAll = svg.append('g');

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
    .enter()
	  .append("line")
	  .filter(function(d) {
	    return linkFilter(d);
	  })
	  .attr('class', function(d) { return "link link-type-"+d.connectiontype; })
	    .style("stroke-opacity", function(d) {
           if(linkIsFake(d)) 
		     return 0.8;            /* fake between ap and radio */
		   else if(linkIsSeen(d))
		     return 0.15;           /* seen between radio and radio */
		   else 
             return 1;            /* p2p link between radio and radio */
		})
	  	.style("stroke", function(d) { 
		   if(linkIsFake(d)) 
		     return "#C1C1C1";      /* fake between radio and radio */
		   else if(linkIsSeen(d)) 
		     return "#bbbbbb";      /* seen link between radio and radio */
		   else 
		   {
		     /* p2p link between radio and radio */
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
             /* p2p link between ap and radio */
			 return 9;    
		   else if(linkIsSeen(d))
		   {
             /* fake link between ap and radio */
		     /* link between radio and radio */
	         if(d.sourcestrength=="") d.sourcestrength = 0;
	         if(d.targetstrength=="") d.targetstrength = 0;
		     return (parseInt(d.sourcestrength)+parseInt(d.targetstrength))/18;
           }
		//	 return 3;
		   else 
		   {
  		     channel = parseInt(graph.nodes[parseInt(d.source.index)].channel);
			 targetchannel = parseInt(graph.nodes[parseInt(d.target.index)].channel);
			 
			 /* source channel != target channel */
             if(channel != targetchannel) return 7;

  			 /* INACTIVE LINK */
			 if(d.state != "Active") return 7;

		     /* link between radio and radio */
	         if(d.sourcestrength=="") d.sourcestrength = 0;
	         if(d.targetstrength=="") d.targetstrength = 0;
		     return (parseInt(d.sourcestrength)+parseInt(d.targetstrength))/18;
		   }
		   })
  		.style("stroke-dasharray", function(d) { 
		     if(linkIsFake(d)) 
			   /* fake link between ap and radio */
			   return "0,0"; 
		     else if(linkIsSeen(d)) 
			   /* seen link between ap and radio */
			   return "6,1"; 
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
			 })
        .on("mouseover", function(d,i) {
		  elm = d3.select(this);
		  if(!elm.attr('ori-stroke-dasharray')) {
		    elm.attr('ori-stroke-dasharray', elm.style('stroke-dasharray'));
		  }
          elm.transition().duration(100).style({'stroke-dasharray':'0,0'});
          })
        .on("mouseout", function(d,i) {
		  elm = d3.select(this);
          elm.transition().duration(200).style({'stroke-dasharray':elm.attr('ori-stroke-dasharray')});
        });

  /* === NODES === */
  
  /* constructs nodes */
  var node = svg.selectAll(".node")
     .data(graph.nodes)
     .enter().append("circle")
	  .attr('class', function(d) { return "node node-type-"+d.type; })
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
   $('svg .link:not(".link-type-fake")').tipsy({ 
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
            if(d.sourcestrength=="") d.sourcestrength = 0;
	        if(d.targetstrength=="") d.targetstrength = 0;
			channel = getSourceChannel(d);
		    return 'Source MAC: '+d.sourcemac+'<br/>Target MAC: '+d.targetmac+'<br/>Source Strength: '+d.sourcestrength+'<br/>Target Strength: '+d.targetstrength+(channel > 0 ? "<br/>"+(channel>=36 ? "5GHz":"2.4GHz")+", Channel "+channel+"" : "")+'<br/>State: '+d.state; 
		  }
        },
		fixTop: 10,
		fixLeft: 240,
      });
	  
	  updateVisibilitySeenLinks();
	  moveSvgElementsToLayer();
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

/* REORDER VISIBILITY */
function moveSvgElementsToLayer() {
  $('svg .link-type-seen').appendTo(layerLinksSeen);
  $('svg .link-type-real').appendTo(layerLinksReal);
  $('svg .link-type-fake').appendTo(layerLinksFake);
  $('svg .node').appendTo(layerNodesAll);
}
  
/* CONTROLS */

$(document).ready(function() {
  $('#visibilitySeenLinks').change(function(){ updateVisibilitySeenLinks(); }).prop('checked',false);
});

function updateVisibilitySeenLinks() {
  d3.selectAll(".link-type-seen").attr("visibility" , $('#visibilitySeenLinks').prop('checked') ? "visible" : "hidden");
}

