define([
    'plugins/netmap-extras',
    'libs-amd/text!netmap/templates/navigation.html',
    'netmap/collections/traffic_gradient',
    'netmap/views/modal/traffic_gradient',
    'netmap/views/searchbox',
    'netmap/views/layer_toggler',
    'netmap/views/categories_toggler',
    'netmap/views/orphans_toggler',
    'netmap/views/position_toggler',
    'netmap/views/algorithm_toggler',
    'netmap/views/topology_error_toggler',
    'netmap/views/mouseover_toggler',
    'libs/handlebars',
    'libs/jquery',
    'libs/underscore',
    'libs/backbone',
    'libs/backbone-eventbroker'
], function (NetmapHelpers, netmapTemplate, TrafficGradientCollection, TrafficGradientView, SearchView, LayerView, CategoryView, OrphanView, PositionView, AlgorithmView, TopologyErrorView, MouseOverView) {

    var NavigationView = Backbone.View.extend({
        broker: Backbone.EventBroker,
        interests: {
            'headerFooterMinimize:trigger': 'headerFooterMinimizeRequest',
            'map:loading:done': 'eventLoadingDone',
            'map:topology_change:loading': 'setLoading'
        },
        events: {
            'click #toggle_view':      'toggleView',
            'click input[name="nodesFixed"]': 'onNodesFixedClick',
            'click input[name="trafficGradient"]': 'onTrafficGradientClick'
        },
        initialize: function () {
            this.gradientView = null;
            this.searchView = null;
            this.categoriesView = null;
            this.orphansView = null;
            this.positionView = null;
            this.layerView = null;
            this.algorithmView = null;

            this.isContentVisible = true;
            this.broker.register(this);

            _.bindAll(this, 'on_keypress');
            $(document).bind('keypress', this.on_keypress);

            this.template = Handlebars.compile(netmapTemplate);

            this.isLoading = !!(this.options.isLoading);

        },
        setLoading: function (state) {
            this.isLoading = state;
            this.render();
        },
        eventLoadingDone: function () {
            this.isLoading = false;
            this.render();
        },
        render: function () {
            var self = this;

            var out = this.template({ isVisible: this.isContentVisible, isLoading: this.isLoading });
            this.$el.html(out);

            this.searchView = this.attachSubView(this.searchView, SearchView, '#search_view');
            this.layerView = this.attachSubView(this.layerView, LayerView, '#layer_view');
            this.categoriesView = this.attachSubView(this.categoriesView, CategoryView, '#categories_view');
            this.orphansView = this.attachSubView(this.orphansView, OrphanView, '#orphan_view');
            this.positionView = this.attachSubView(this.positionView, PositionView, '#position_view');
            this.algorithmView = this.attachSubView(this.algorithmView, AlgorithmView, '#algorithm_view');
            this.topologyErrorsView = this.attachSubView(this.topologyErrorsView, TopologyErrorView, '#topology_errors_view');
            this.mouseOverView = this.attachSubView(this.mouseOverView, MouseOverView, '#mouseover_view');

            return this;
        },
        alignView: function () {
            var $helper = $(this.$el);
            var $helper_content = $(".inner_wrap.left_sidebar", this.$el);

            var margin;

            if (!this.isContentVisible) {
                margin = 30;
                $helper.animate({'width': "{0}px".format(12) }, 400);
                $helper_content.fadeOut('fast');

                $("a#toggle_view", this.$el).html("&gt;&gt;");

            } else {
                margin = 170;

                $helper_content.fadeIn('fast');
                $helper.animate({'width': "{0}px".format(margin-40) }, 400);

                $("a#toggle_view", this.$el).html("&lt;&lt;");

            }

            return margin;
            //$("#netmap_main_view").animate({'margin-left': "{0}px".format(margin)}, 400);

        },
        headerFooterMinimizeRequest: function (options) {
            if (options && options.name === 'header' && (options.isShowing !== this.isContentVisible)) {
                this.toggleView();
            }
        },
        toggleView: function (e) {
            this.isContentVisible = !this.isContentVisible;
            var margin = this.alignView();
            this.broker.trigger('map:resize:animate', {marginLeft: margin});
        },
        onNodesFixedClick: function (e) {
            var val = $(e.currentTarget).val();
            if (val === 'Fix') {
                this.broker.trigger('map:fixNodes', true);
            } else if (val === 'UnFix') {
                this.broker.trigger('map:fixNodes', false);
            }
        },
        onTrafficGradientClick: function (e) {
            var self = this;
            if (this.gradientView) {
                this.gradientView.close();
            }

            var gradientModel = new TrafficGradientCollection();
            gradientModel.fetch({
                success: function (model) {
                    self.gradientView = new TrafficGradientView({collection: model});
                    self.gradientView.render();
                }
            });

        },
        on_keypress: function (e) {
            if (e.charCode === 110) { // n
                this.context.ui.mouseover.nodes.state = !this.context.ui.mouseover.nodes.state;
                this.broker.trigger('map:ui:mouseover:nodes', this.context.ui.mouseover.nodes.state);
            } else if (e.charCode === 108) { // l
                this.context.ui.mouseover.links.state = !this.context.ui.mouseover.links.state;
                this.broker.trigger('map:ui:mouseover:links', this.context.ui.mouseover.links.state);
            }
            this.render();
        },
        close:function () {
            this.layerView.close();
            $(document).unbind('keypress', 'on_keypress');
            this.broker.unregister(this);
            $(this.el).unbind();
            $(this.el).remove();
        }
    });
    return NavigationView;
});





