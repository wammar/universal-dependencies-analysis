function showResponseInfo(size, time){
    $('#response_info').text("Found "+ size + " results in "+ time + "ms")
}

function showResponseError(size, time){
    $('#response_info').text("Bad Query")
}

function showResultsNavigation(){
    $("#results_navigation").removeClass('hide');
}

function draw_flat_data(data){
    output = convert_flat_data(data);
    treeData = output[0]
    treeSize = output[1]
    draw_tree(treeData, treeSize);
}

function convert_flat_data(data){
    // create a name: node map
    var dataMap = data.reduce(function(map, node) {
        map[node.name] = node;
        return map;
    }, {});

    // create the tree array
    var tree = [];
    data.forEach(function(node) {
        // add to parent
        var parent = dataMap[node.parent];
        if (parent) {
            // create child array if it doesn't exist
            (parent.children || (parent.children = []))
                // add node to child array
                .push(node);
        } else {
            // parent is null or missing
            tree.push(node);
        }
    });
    return [tree, data.length];
}

function draw_tree(treeData, treeSize){
    // remove previous diagram
    d3.select("svg").remove();

    // ************** Generate the tree diagram  *****************
    var margin = {top: 20, right: 120, bottom: 20, left: 120},
     width = treeSize*70 - margin.right - margin.left,
     height = 2000 - margin.top - margin.bottom;

    var i = 0;

    var tree = d3.layout.tree()
     .size([height, width]);

    var diagonal = d3.svg.diagonal()
     .projection(function(d) { return [d.x, d.y]; });

    var svg = d3.select("body").append("svg")
     .attr("width", width + margin.right + margin.left)
     .attr("height", height + margin.top + margin.bottom)
      .append("g")
     .attr("transform", "translate(" + margin.left + "," + margin.top + ")");



    root = treeData[0];

    update(root);

    // Splitting labels
    var insertLinebreaks = function (d) {
        var el = d3.select(this);
        var words = d.name.split('\n');
        el.text('');

        for (var i = 0; i < words.length; i++) {
            var tspan = el.append('tspan').text(words[i]);
            if (i > 0)
                tspan.attr('x', 0).attr('dy', '15');
        }
    };
    svg.selectAll('.mynodelabel').each(insertLinebreaks);

    // svg.selectAll('.mylabel').attr("transform","rotate(90)");

    function update(source) {

      // Compute the new tree layout.
      var nodes = tree.nodes(root).reverse(),
       links = tree.links(nodes);

      // Normalize for fixed-depth.
      nodes.forEach(function(d) { d.y = d.depth * 180; });
      nodes.forEach(function(d) { d.x = d.xpos * 60; });

      // Declare the nodesâ€¦
      var node = svg.selectAll("g.node")
       .data(nodes, function(d) { return d.id || (d.id = ++i); });

      // Enter the nodes.
      var nodeEnter = node.enter().append("g")
       .attr("class", "node")
       .attr("transform", function(d) {
        return "translate(" + d.x + "," + d.y + ")"; });

      nodeEnter.append("circle")
       .attr("r", 25)
       .style("fill", function(d){ return d.match ? "#228B22": "#fff"});

      nodeEnter.append("text")
        .attr("class", "mynodelabel")
       .attr("x", function(d) {
        return 0 })
       .attr("y", function(d) {
        return -5 })
       .attr("dy", ".20em")
       .attr("text-anchor", "middle")
       .text(function(d) {return d.name;})
       .style("fill-opacity", 1);

      // Declare the linksâ€¦
      var link = svg.selectAll("path.link")
       .data(links, function(d) { return d.target.id; });

    function arcPath(leftHand, d) {
            var start = leftHand ? d.source : d.target,
                end = leftHand ? d.target : d.source,
                dx = end.x - start.x,
                dy = end.y - start.y,
                dr = Math.sqrt(dx * dx + dy * dy),
                sweep = leftHand ? 0 : 1;
            return "M" + start.x + "," + start.y + "A" + dr + "," + dr +
                " 0 0," + sweep + " " + end.x + "," + end.y;
        }

      // Enter the links.
      link.enter().insert("path", "g")
       .attr("class", "link")
       .attr("d", diagonal);

      // Enter link labels
      link.enter().insert("text", "g")
          .attr("dx", 30)
          .attr("transform", function (d) {
                    return "rotate(-90 "+ (d.target.x)+ " "+ (d.target.y) +") translate(" + (d.target.x) + "," + (d.target.y) + ")"; })
          .text(function(d) { return d.target.edgelabel; })

//                    .attr("x", function(d) { return (; })
//          .attr("y", function(d) { return (; })




    }
}

