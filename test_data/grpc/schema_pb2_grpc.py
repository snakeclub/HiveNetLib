# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import schema_pb2 as schema__pb2


class GatewayStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.Call = channel.stream_stream(
        '/schema.Gateway/Call',
        request_serializer=schema__pb2.Request.SerializeToString,
        response_deserializer=schema__pb2.Response.FromString,
        )


class GatewayServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def Call(self, request_iterator, context):
    # missing associated documentation comment in .proto file
    pass
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_GatewayServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'Call': grpc.stream_stream_rpc_method_handler(
          servicer.Call,
          request_deserializer=schema__pb2.Request.FromString,
          response_serializer=schema__pb2.Response.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'schema.Gateway', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
